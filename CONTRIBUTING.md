# 参与与贡献

这个仓库是 `openjm` 三仓里的**总仓**：协议、需求、测试、流程都在这儿，实现分别在 `openjm-sdk` 与 `openjm-mobile`。

动手前先读两篇，能省掉后面大部分返工：

1. [`docs/process/iteration.md`](docs/process/iteration.md) —— 分支怎么开、提交怎么写、PR 装什么、协议改动走哪条线；
2. [`docs/process/doc-rules.md`](docs/process/doc-rules.md) —— 文档放哪、怎么写、什么时候必须同步。

快速验证环境是否可用：

```bash
git clone https://github.com/qichen-sbgh/openjm-sdk ../openjm-sdk
pip install -e ../openjm-sdk
OPENJM_KEY_FILE="$PWD/testvectors/keys.test.json" python -m openjm verify testvectors/valid/v01-plain-no-pad.jm
python3 .github/scripts/check_vectors.py
```

三条底线：

- `main` 永远可构建、CI 永远绿；
- 改协议字节语义必须升版本号并重生成向量，不许在 v1 上做兼容微调；
- 不提交密钥、真实文档和 `.jm` 样本（`testvectors/` 的公开测试密钥除外）。
