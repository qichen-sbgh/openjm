# 移动端设计

| 项 | 值 |
| --- | --- |
| 状态 | 生效：Android 导入链路 + PDFium 渲染已实现并有 host 测试；封面与进度落库未接 |
| 最后更新 | 2026-11-27 |
| 代码 | [`openjm-mobile`](https://github.com/qichen-sbgh/openjm-mobile) |
| 关联协议 | [`protocol.md`](protocol.md) |

## 1. 模块划分

```text
openjm-mobile/
├── shared/                        # KMP：协议、数据、UI 全共享
│   ├── commonMain/kotlin/com/openjm/reader/
│   │   ├── crypto/   JmProtocol / JmKeyDerivation / JmPrimitives(expect) /
│   │   │             JmMeta / JmImporter / JmErrors
│   │   ├── data/     Book + BookRepository（Room KMP 待接入）
│   │   └── ui/       App（书架） / PdfReaderCanvas(expect)
│   ├── androidMain/  javax.crypto、ContentResolver 流、PDFium 占位
│   └── iosMain/      CommonCrypto、NSInputStream、PDFKit 占位、ComposeUIViewController
├── androidApp/                    # 薄壳：QQ 唤起、SAF 兜底、私有沙盒
└── iosApp/                        # 薄壳：自定义 UTI + onOpenURL
```

> 与原设计文档的一处偏离：原文写单个 `composeApp` 模块。改成 `shared + androidApp + iosApp`，
> 因为 Manifest 与 Info.plist 需要各平台原生入口，拆开后壳工程可以很薄。功能边界不变。

## 2. QQ 唤起兼容矩阵

| 平台 | 坑 | 策略 |
| --- | --- | --- |
| Android | QQ 常发 `application/octet-stream`，`content://` 里没有 `.jm` 后缀 | 一律读前 4 字节校验 `JM01` 魔数，不看后缀 |
| Android | 偶发改名成 `.jm.1` | 魔数判定天然兼容 |
| Android | 11+ 分区存储拿不到物理路径 | 只用 `ContentResolver.openInputStream`，不碰路径 |
| Android | 部分国产 ROM 拦截三方文件关联 | 首页常驻“导入 .jm”（SAF `OpenDocument`）兜底 |
| iOS | 未知后缀不出现在 QQ“用其他应用打开” | `Info.plist` 注册 `UTExportedTypeDeclarations` + `CFBundleDocumentTypes`，`onOpenURL` 接管 |

## 3. 单遍流式导入

`ContentResolver` / `NSInputStream` 都不支持 seek，所以校验与解密必须一遍完成：

```text
读 28B 头 ──▶ 决定要不要口令 ──▶ 派生密钥
   │
   └─▶ 循环读 64KB：保留尾部 32B（这 32B 是 HMAC，不能参与 HMAC 计算）
           ├─ HMAC.update(body)
           └─ cipher.update(body) ──▶ Meta 段攒着解析 / Payload 段写 sink / 填充段丢弃
   │
   └─▶ EOF：held 必须正好 32B，常量时间比对，再断言长度恒等式
```

**只有 `import` 正常返回后才允许把临时文件转正**。中途失败删 `.tmp`，这样绝不会有“能打开的半个文档”。

## 4. 三端对齐的两个坑

1. **CTR 计数器必须大端**。Android `AES/CTR/NoPadding` 默认就是大端；iOS 上如果走 `CCCryptorCreateWithMode` 忘了 `kCCModeOptionCTR_BE`，结果与另两端完全不同。当前实现绕开该选项：用 ECB 批量加密计数器块再异或，计数器进位由 Kotlin 显式做大端递增。
2. **PBKDF2 的口令编码**。Python 用 `password.encode("utf-8")` 的**字节**；Android `PBEKeySpec` 吃 `char[]`，必须把 UTF-8 字节还原成 String 再转 char[]；iOS `CCKeyDerivationPBKDF` 直接吃字节，不用转换。

## 5. 书架数据

主键 `docId`（来自加密 Meta），重复导入命中同一条时**保留** `lastPage` / `totalPages` / `scrollRatio`，只刷新 `lastReadAt` 与文件有效性。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `docId` | String | 主键，`doc_id` |
| `title` | String | 展示标题，可重命名 |
| `ext` | String | 原始扩展名，用于路由阅读组件 |
| `localPath` | String | 沙盒内相对路径 |
| `coverPath` | String? | 封面缩略图相对路径 |
| `fileSize` | Long | 明文大小 |
| `lastPage` / `totalPages` | Int | 上次页码（0 起）/ 总页数 |
| `scrollRatio` | Float | 纵向滚动比例，防横竖屏跑偏 |
| `importedAt` / `lastReadAt` | Long | 导入 / 最近阅读时间戳（默认排序依据） |

## 6. 阅读器桥与进度

```kotlin
@Composable
expect fun PdfReaderCanvas(
    filePath: String,
    initialPage: Int,
    initialScrollRatio: Float,
    onDocumentLoaded: (totalPages: Int) -> Unit,
    onProgressChanged: (page: Int, scrollRatio: Float) -> Unit,
    modifier: Modifier = Modifier,
)
```

进度保存 **500ms 防抖**，页面退出（`onDispose`）或切后台时补写一次最终进度。

## 7. 当前进度与待办

已写：协议核心（头解析、HKDF、Meta、单遍导入）、两端加密原语、两端壳入口、书架 UI 骨架；
导入落盘链路（`tmp/` 半成品 → 校验通过原子改名 `books/{doc_id}.{ext}` → 书架按 `doc_id` upsert），
`androidHostTest` 用冻结向量断言了落盘位置、临时文件清理与去重语义；
PDF 渲染（`io.legere:pdfiumandroid`，纵向分页列表 + 首页比例占位，离屏 Bitmap 随列表回收）与阅读页；
首帧封面（WebP，`covers/{doc_id}.webp`，书架 48×64dp 缩略图，失败退回占位块）。
整条链路已在 Android 16 模拟器上端到端跑通：VIEW 唤起 → 导入落盘 → 书架 → 阅读 → 进度回填。

未做：口令弹窗（当前只提示“需要口令”）、Room KMP + KSP 持久化（书架与进度都在内存，重启即清空）、
页内偏移恢复（`initialScrollRatio` 已透传但未消费）、真机兼容验证。
清单维护在仓库 README，不在本文档复制一遍。

## 8. 已知代价

- **APK 体积**：`pdfiumandroid` 的 AAR 带 arm64-v8a / armeabi-v7a / x86 / x86_64 四套 `libpdfium.so`，
  debug APK 从 11.5MB 涨到 29MB。群内直发前要配 ABI split，或只保留 arm64-v8a（覆盖绝大多数机型）。
- **渲染无法自动化**：PDFium 是 Android 原生库，跑不了 host 测试，效果只能进真机清单 §3.3。
