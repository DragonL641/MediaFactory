// MediaFactory 桌面壳：拉起 daemon → 等端口就绪 → 显示窗口加载 Web UI → 退出带走 daemon。
// 唯一职责是进程生命周期管理，不含业务逻辑（改业务请去 SPA 或 daemon）。
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use tauri::{AppHandle, Manager, RunEvent};

const DAEMON_HOST: &str = "127.0.0.1";
const DAEMON_PORT: u16 = 8765;
/// 就绪超时：含 ML 依赖冷启动（首次解压、模型扫描）
const READY_TIMEOUT_SECS: u64 = 120;
/// 优雅停机等待：daemon 收 RUNNING 任务（协作式取消在句边界生效，可能数秒）
const SHUTDOWN_TIMEOUT_SECS: u64 = 15;
/// 实例锁让位特征码：daemon 撞锁退出时使用，壳据此区分双启动让位（42）与真崩溃
const LOCK_YIELDED_EXIT_CODE: i32 = 42;
const POLL_INTERVAL: Duration = Duration::from_millis(300);

/// 壳持有的 daemon 子进程；复用已运行实例时为 None（退出时不杀别人的 daemon）
#[derive(Default)]
struct DaemonHandle {
    child: Option<Child>,
    /// 壳主动退出中：此间 daemon 之死是预期收尾，监护线程不弹崩溃框
    shutting_down: bool,
}

fn daemon_addr() -> SocketAddr {
    SocketAddr::from(([127, 0, 0, 1], DAEMON_PORT))
}

fn port_ready() -> bool {
    // uvicorn 在 lifespan startup 完成后才开始 accept，TCP 连通 = API 完全就绪；
    // connect_timeout 防 backlog 病态满载时连接无限挂起
    TcpStream::connect_timeout(&daemon_addr(), Duration::from_secs(2)).is_ok()
}

fn daemon_exe_path(app: &AppHandle) -> Option<PathBuf> {
    let dir = app.path().resource_dir().ok()?.join("python-backend");
    let exe = if cfg!(target_os = "windows") {
        dir.join("MediaFactory.exe")
    } else {
        dir.join("MediaFactory")
    };
    exe.is_file().then_some(exe)
}

fn spawn_daemon(app: &AppHandle) -> Option<Child> {
    let exe = daemon_exe_path(app)?;
    let mut cmd = Command::new(&exe);
    cmd.current_dir(exe.parent()?);
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        // 独立进程组：硬杀兜底时可 killpg 整组收割（含 worker 子进程）
        cmd.process_group(0);
    }
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }
    cmd.spawn().ok()
}

/// POST /api/system/shutdown（手写 HTTP，避免引入 HTTP 客户端依赖）
fn request_http_shutdown() {
    // 连接/读/写全设超时：daemon 僵死时不能无限挂起，否则硬杀兜底被架空
    let addr = daemon_addr();
    let Ok(mut stream) = TcpStream::connect_timeout(&addr, Duration::from_secs(2)) else {
        eprintln!("[mediafactory-shell] shutdown endpoint unreachable: {addr}");
        return;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_secs(2)));
    let _ = stream.set_write_timeout(Some(Duration::from_secs(2)));
    let req = format!(
        "POST /api/system/shutdown HTTP/1.1\r\nHost: {DAEMON_HOST}:{DAEMON_PORT}\r\n\
         Content-Length: 0\r\nConnection: close\r\n\r\n"
    );
    let _ = stream.write_all(req.as_bytes());
    let _ = stream.read(&mut [0u8; 512]); // 等响应落盘，确保 daemon 已受理（读超时兜底）
}

/// 致命错误：弹窗提示后退出壳（spec：进程意外退出 → 提示而非白屏）
/// 注：blocking_show 阻塞至弹窗关闭，只能非主线程调用（fatal 均来自后台监护线程）
fn fatal(app: &AppHandle, msg: &str) {
    use tauri_plugin_dialog::{DialogExt, MessageDialogKind};
    let _ = app
        .dialog()
        .message(msg)
        .kind(MessageDialogKind::Error)
        .title("MediaFactory")
        .blocking_show();
    app.exit(1);
}

/// 壳是否已进入主动退出流程（此间 daemon 之死是预期，不弹错误框）
fn is_shutting_down(state: &Arc<Mutex<DaemonHandle>>) -> bool {
    state.lock().unwrap().shutting_down
}

/// 后台监护线程：拉起/复用 daemon → 等就绪 → 显示窗口 → 持续监视 daemon 生死
fn launch_supervisor(app: AppHandle, state: Arc<Mutex<DaemonHandle>>) {
    std::thread::spawn(move || {
        // 复用已运行 daemon（用户误双击第二次启动），否则 spawn 新进程
        let child = if port_ready() {
            log("daemon 已在运行，直接连接");
            None
        } else if cfg!(debug_assertions) {
            // 开发模式（tauri dev）：不 spawn 打包产物，
            // 等开发者手动 `uv run python -m mediafactory`
            log("开发模式：等待外部启动的 daemon (127.0.0.1:8765)");
            None
        } else {
            match spawn_daemon(&app) {
                Some(c) => Some(c),
                None => {
                    fatal(&app, "Failed to start backend service (python-backend missing or corrupted)");
                    return;
                }
            }
        };
        state.lock().unwrap().child = child;

        // 等端口就绪
        let deadline = Instant::now() + Duration::from_secs(READY_TIMEOUT_SECS);
        while !port_ready() {
            if Instant::now() > deadline {
                if !is_shutting_down(&state) {
                    fatal(&app, "Backend service startup timed out. Please retry or check the logs.");
                }
                return;
            }
            let mut guard = state.lock().unwrap();
            if let Some(c) = guard.child.as_mut() {
                if let Ok(Some(status)) = c.try_wait() {
                    if status.code() == Some(LOCK_YIELDED_EXIT_CODE) {
                        // 撞实例锁让位（退出码 42）：先发实例将继续服务，转复用语义（不杀不监护）
                        guard.child = None;
                        drop(guard);
                        log("另一个 daemon 实例已在运行，接管连接");
                        continue;
                    }
                    let shutting_down = guard.shutting_down;
                    drop(guard);
                    if !shutting_down {
                        // 非 42 秒退 = 真崩溃，立即报错
                        fatal(&app, "Backend service exited unexpectedly during startup");
                    }
                    return;
                }
            }
            std::thread::sleep(POLL_INTERVAL);
        }

        // 竞态兜底：端口就绪从循环顶部（P1）退出时，本壳 spawn 的 child 若恰在同轮死亡
        // 仍是 Some(已死)，监护循环会误判崩溃——统一规范化为复用语义
        {
            let mut guard = state.lock().unwrap();
            if matches!(guard.child.as_mut().map(|c| c.try_wait()), Some(Ok(Some(_)))) {
                guard.child = None;
                log("接管先发实例的 daemon");
            }
        }

        if let Some(window) = app.get_webview_window("main") {
            let _ = window.show();
            let _ = window.set_focus();
        }

        // 持续监护：daemon 意外退出（非壳主动关闭）→ 提示并退出壳
        loop {
            std::thread::sleep(Duration::from_secs(2));
            let mut guard = state.lock().unwrap();
            if guard.shutting_down {
                return; // 壳主动退出中：daemon 之死是预期收尾，不弹崩溃框
            }
            let alive = match guard.child.as_mut() {
                Some(c) => matches!(c.try_wait(), Ok(None)),
                None => port_ready(), // 复用模式：原 daemon 退出则本壳失去意义
            };
            if !alive {
                drop(guard);
                fatal(&app, "Backend service exited. Task state will be recovered on next launch.");
                return;
            }
        }
    });
}

/// 壳退出路径：优雅 shutdown → 等退出 → 硬杀进程树兜底
fn shutdown_daemon(state: &Arc<Mutex<DaemonHandle>>) {
    let mut guard = state.lock().unwrap();
    // 立即置位（先于任何 kill 动作）：监护线程此后见标志即收手，正常退出不弹假崩溃框
    guard.shutting_down = true;
    let Some(child) = guard.child.as_mut() else {
        return; // 复用模式：不杀不属于本壳的 daemon
    };
    let pid = child.id();

    // 优雅路径：daemon 走 lifespan 收尾（RUNNING 落 CANCELLED）+ atexit 释放锁
    request_http_shutdown();

    let deadline = Instant::now() + Duration::from_secs(SHUTDOWN_TIMEOUT_SECS);
    loop {
        if let Ok(Some(_)) = child.try_wait() {
            return; // 已优雅退出
        }
        if Instant::now() > deadline {
            break;
        }
        std::thread::sleep(POLL_INTERVAL);
    }

    // 硬杀兜底（进程树含 worker 子进程）
    eprintln!("[mediafactory-shell] graceful shutdown timed out, killing pid={pid}");
    #[cfg(unix)]
    unsafe {
        libc::killpg(pid as i32, libc::SIGKILL);
    }
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        let _ = Command::new("taskkill")
            .args(["/PID", &pid.to_string(), "/T", "/F"])
            .creation_flags(CREATE_NO_WINDOW)
            .status();
    }
    let _ = child.wait();
}

/// 壳内日志（Rust 侧无文件日志，输出到 stderr 便于 tauri dev 排查）
fn log(msg: &str) {
    eprintln!("[mediafactory-shell] {msg}");
}

fn main() {
    let handle_state: Arc<Mutex<DaemonHandle>> = Arc::new(Mutex::new(DaemonHandle::default()));

    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup({
            let state = handle_state.clone();
            move |app| {
                launch_supervisor(app.handle().clone(), state);
                Ok(())
            }
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(move |_app_handle, event| {
        if let RunEvent::ExitRequested { .. } = event {
            shutdown_daemon(&handle_state);
        }
    });
}
