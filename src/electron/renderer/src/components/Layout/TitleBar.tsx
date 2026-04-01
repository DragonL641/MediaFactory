/**
 * 自定义顶部栏
 *
 * 深色背景，包含 logo 和窗口控制按钮
 * macOS 预留 traffic light 按钮空间，Windows 显示窗口控制按钮
 */

import React, { useEffect, useState } from "react";
import { MinusOutlined, BorderOutlined, CloseOutlined } from "@ant-design/icons";

const TITLEBAR_HEIGHT = 44;

const TitleBar: React.FC = () => {
  const [isMac, setIsMac] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);

  useEffect(() => {
    window.electronAPI.getPlatform().then((info) => {
      setIsMac(info.isMac);
    });
    window.electronAPI.windowIsMaximized().then(setIsMaximized);
  }, []);

  const handleMinimize = () => {
    window.electronAPI.windowMinimize();
  };

  const handleMaximize = async () => {
    await window.electronAPI.windowMaximize();
    const maximized = await window.electronAPI.windowIsMaximized();
    setIsMaximized(maximized);
  };

  const handleClose = () => {
    window.electronAPI.windowClose();
  };

  return (
    <div className="top-bar">
      {/* macOS：左侧预留 traffic light 按钮空间 */}
      {isMac && <div style={{ width: 78 }} />}

      {/* Logo */}
      <div className="top-bar-logo">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="m20.2 6-3-3H7L4 6" />
          <path d="M4 6v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6" />
          <path d="M15.5 11a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Z" />
          <path d="m2 2 2.4 2.4" />
          <path d="m20 2-2.4 2.4" />
        </svg>
        <span>MediaFactory</span>
      </div>

      {/* Windows：右侧窗口控制按钮 */}
      {!isMac && (
        <div className="top-bar-controls">
          <button className="top-bar-btn" onClick={handleMinimize} title="Minimize">
            <MinusOutlined style={{ fontSize: 12 }} />
          </button>
          <button className="top-bar-btn" onClick={handleMaximize} title="Maximize">
            <BorderOutlined style={{ fontSize: 11 }} />
          </button>
          <button className="top-bar-btn top-bar-btn-close" onClick={handleClose} title="Close">
            <CloseOutlined style={{ fontSize: 12 }} />
          </button>
        </div>
      )}
    </div>
  );
};

export default TitleBar;
export { TITLEBAR_HEIGHT };
