## 这次改了什么

<!-- 一句话说清，别写“若干优化” -->

## 影响面

<!-- 至少勾一项，用来触发 docs/process/iteration.md §7 的同步检查 -->

- [ ] 需求（动了 `docs/requirements/`，需同步追溯矩阵）
- [ ] 协议字节语义（需升版本 + 重生成向量 + 两仓 `compatible:` 同步）
- [ ] 实现行为（需带测试）
- [ ] 测试向量（说明新增/调整的覆盖点）
- [ ] 文档结构 / 流程（需更新 `docs/README.md` 导航）
- [ ] 仅构建 / CI

## 验证

<!-- 贴命令与结果；手工验证写清步骤 -->

```bash
python3 .github/scripts/check_vectors.py
OPENJM_TESTVECTORS="$PWD/testvectors" python -m pytest ../openjm-sdk/tests/test_conformance.py -q
```

## 自查清单

- [ ] CI 绿
- [ ] 行为变更带了测试，或写明了手工验证步骤与结果
- [ ] 按影响面同步了文档（需求 / 技术 / 测试）
- [ ] 没有提交密钥、真实文档或 `.jm` 样本
- [ ] CHANGELOG 加了一行
