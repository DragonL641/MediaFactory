// MediaFactory 桌面壳：拉起 daemon → 等端口就绪 → 显示窗口加载 Web UI → 退出带走 daemon。
// 唯一职责是进程生命周期管理，不含业务逻辑（改业务请去 SPA 或 daemon）。
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{Read, Write};
use std::net::TcpStream;
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
const POLL_INTERVAL: Duration = Duration::from_millis(300);

/// 壳持有的 daemon 子进程；复用已运行实例时为 None（退出时不杀别人的 daemon）
#[derive(Default)]
struct DaemonHandle {
    child: Option<Child>,
}

fn port_ready() -> bool {
    // uvicorn 在 lifespan startup 完成后才开始 accept，TCP 连通 = API 完全就绪
    TcpStream::connect((DAEMON_HOST, DAEMON_PORT)).is_ok()
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
    if let Ok(mut stream) = TcpStream::connect((DAEMON_HOST, DAEMON_PORT)) {
        let req = format!(
            "POST /api/system/shutdown HTTP/1.1\r\nHost: {DAEMON_HOST}:{DAEMON_PORT}\r\n\
             Content-Length: 0\r\nConnection: close\r\n\r\n"
        );
        let _ = stream.write_all(req.as_bytes());
        let _ = stream.read(&mut [0u8; 512]); // 等响应落盘，确保 daemon 已受理
    }
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

/// 后台监护线程：拉起/复用 daemon → 等就绪 → 显示窗口 → 持续监视 daemon 生死
fn launch_supervisor(app: AppHandle, state: Arc<Mutex<DaemonHandle>>) {
    std::thread::spawn(move || {
        // 复用已运行 daemon（用户误双击第二次启动），否则 spawn 新进程
        let child = if port_ready() {
            log(&app, "daemon 已在运行，直接连接");
            None
        } else if cfg!(debug_assertions) {
            // 开发模式（tauri dev）：不 spawn 打包产物，
            // 等开发者手动 `uv run python -m mediafactory`
            log(&app, "开发模式：等待外部启动的 daemon (127.0.0.1:8765)");
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
                fatal(&app, "Backend service startup timed out. Please retry or check the logs.");
                return;
            }
            // spawn 的 daemon 秒退（崩溃等）——若期间端口被其他实例接上则转复用，否则报错
            let mut guard = state.lock().unwrap();
            if let Some(c) = guard.child.as_mut() {
                if matches!(c.try_wait(), Ok(Some(_))) && !port_ready() {
                    drop(guard);
                    fatal(&app, "Backend service exited unexpectedly during startup");
                    return;
                }
            }
            std::thread::sleep(POLL_INTERVAL);
        }

        if let Some(window) = app.get_webview_window("main") {
            let _ = window.show();
            let _ = window.set_focus();
        }

        // 持续监护：daemon 意外退出（非壳主动关闭）→ 提示并退出壳
        loop {
            std::thread::sleep(Duration::from_secs(2));
            let mut guard = state.lock().unwrap();
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
    let Some(child) = guard.child.as_mut() else {
        return; // 复用模式：不杀不属于本壳的 daemon
    };
    let pid = child.id();

    // 优雅路径：daemon 走 lifespan 收尾（RUNNING 落 CANCELLED）+ atexit 释放锁
    request_http_shutdown();

    let deadline = Instant::now() + Duration::from_secs(SHUTDOWN_TIMEOUT_SECS);
    loop {
        match child.try_wait() {
            Ok(Some(_)) => return, // 已优雅退出
            _ => {}
        }
        if Instant::now() > deadline {
            break;
        }
        std::thread::sleep(POLL_INTERVAL);
    }

    // 硬杀兜底（进程树含 worker 子进程）
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
fn log(app: &AppHandle, msg: &str) {
    let _ = app;
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

    app.run(move |app_handle, event| {
        if let RunEvent::ExitRequested { .. } = event {
            shutdown_daemon(&handle_state);
            let _ = app_handle;
        }
    });
}
