/**
 * 服务端目录浏览器
 *
 * 替代 Electron 原生文件对话框：列出 daemon 侧目录，点选文件回传绝对路径。
 */

import { ArrowUpOutlined, FileOutlined, FolderOutlined } from "@ant-design/icons";
import { Alert, Button, List, Modal, Space, Spin, Typography } from "antd";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { getApiClient } from "../api/client";

interface BrowseEntry {
  name: string;
  is_dir: boolean;
}

interface BrowseResult {
  path: string;
  parent: string | null;
  entries: BrowseEntry[];
}

interface BrowseModalProps {
  open: boolean;
  /** 允许的文件扩展名（小写、无点），如 ["mp4", "mkv"]；缺省不过滤 */
  extensions?: string[];
  onCancel: () => void;
  /** 选中文件（绝对路径）后回调 */
  onSelect: (path: string) => void;
}

const BrowseModal: React.FC<BrowseModalProps> = ({
  open,
  extensions,
  onCancel,
  onSelect,
}) => {
  const { t } = useTranslation("forms");
  const [current, setCurrent] = useState<string>("");
  const [parent, setParent] = useState<string | null>(null);
  const [entries, setEntries] = useState<BrowseEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (path?: string) => {
      setLoading(true);
      setError(null);
      try {
        const client = getApiClient();
        const resp = await client.get<BrowseResult>("/api/system/browse", {
          params: {
            path: path || undefined,
            ext: extensions?.join(","),
          },
        });
        setCurrent(resp.data.path);
        setParent(resp.data.parent);
        setEntries(resp.data.entries);
      } catch {
        setError(t("pathInput.loadError"));
      } finally {
        setLoading(false);
      }
    },
    [extensions, t]
  );

  useEffect(() => {
    if (open && !current) {
      void load(); // 首次打开从用户主目录开始
    }
  }, [open, current, load]);

  const joinPath = (dir: string, name: string) =>
    dir.endsWith("/") || dir.endsWith("\\") ? `${dir}${name}` : `${dir}/${name}`;

  const handleSelect = (path: string) => {
    onSelect(path);
    onCancel();
  };

  return (
    <Modal
      title={t("pathInput.browseTitle")}
      open={open}
      onCancel={onCancel}
      footer={null}
      width={640}
    >
      <Space direction="vertical" style={{ width: "100%" }}>
        <Space>
          <Button
            icon={<ArrowUpOutlined />}
            disabled={!parent}
            onClick={() => void load(parent ?? undefined)}
          >
            {t("pathInput.up")}
          </Button>
          <Typography.Text code ellipsis style={{ maxWidth: 420 }}>
            {current}
          </Typography.Text>
        </Space>
        {error && <Alert type="error" showIcon message={error} />}
        {loading ? (
          <Spin style={{ display: "block", margin: "24px auto" }} />
        ) : (
          <List
            size="small"
            style={{ maxHeight: 360, overflowY: "auto" }}
            dataSource={entries}
            locale={{ emptyText: t("pathInput.empty") }}
            renderItem={(entry) => (
              <List.Item
                style={{ cursor: "pointer" }}
                onClick={() =>
                  entry.is_dir
                    ? void load(joinPath(current, entry.name))
                    : handleSelect(joinPath(current, entry.name))
                }
              >
                <Space>
                  {entry.is_dir ? <FolderOutlined /> : <FileOutlined />}
                  <span>{entry.name}</span>
                </Space>
              </List.Item>
            )}
          />
        )}
      </Space>
    </Modal>
  );
};

export default BrowseModal;
