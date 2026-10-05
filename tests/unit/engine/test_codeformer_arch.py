"""codeformer_arch vendored 网络的最小验证（随机权重，不需要下载）"""

import pytest

pytestmark = [pytest.mark.unit]


class TestCodeFormerArch:
    def test_forward_shape_and_range(self):
        torch = pytest.importorskip("torch")
        from mediafactory.engine.enhancement.codeformer_arch import CodeFormer

        net = CodeFormer(dim_embd=512, n_head=8, codebook_size=1024)
        net.eval()
        x = torch.rand(1, 3, 512, 512) * 2 - 1  # [-1, 1]
        with torch.no_grad():
            out, logits, lq_feat = net(x, w=0.7)
        assert out.shape == (1, 3, 512, 512)
        assert logits.shape == (1, 256, 1024)  # 512 输入 → 16x16 latent 位置
        assert lq_feat.shape == (1, 256, 16, 16)
        assert torch.isfinite(out).all()
