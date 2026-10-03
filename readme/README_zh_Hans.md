# 通义 AIGC

## 0.0.5 — 百炼最新 AIGC 模型（2026-10-03）

- 新增 `qwen-image-3.0-pro` / `qwen-image-3.0` 文生图与图像编辑，支持 `prompt_extend_mode` 和 `enable_thinking`。图生图只支持 direct；agent 仅用于文生图。不再以800字符截断提示词，Token限制由百炼处理。
- 补齐 Qwen 2.0 Pro 的 2026-06-22 / 2026-04-22 快照，以及 Wan 2.7 视频快照、Wan 2.6 i2v-flash。
- 新增 `wan_video`：`wan3.0-video` / `wan3.0-video-prime`，支持文生视频、首尾帧、多模态参考、文档/网页、编辑和延长视频。480P/720P/1080P，2–30秒或 -1 智能时长。
- 新增 `wan_video_edit`：`wan2.7-videoedit`，指令编辑及最多4张参考图。新视频工具提交异步任务，将返回的 task_id 传给 `wan_video_query` 查询。
- 新增可选凭据 `api_base_url`，所有提交与查询共用此地域/业务空间域名。默认北京旧域名兼容已有配置；Wan3 请填写实际业务空间域名，例如 `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com`。模型、API Key 与域名必须属于同一地域。
- Qwen 默认升级为3.0 Pro；Wan视频默认升级为2.7；HappyHorse Python 默认值与1.1配置对齐。已有工作流显式选择的旧模型保持可用。

### Wan3 使用示例

文生视频：选择 `wan_video`，填提示词，`media` 留空。首尾帧：填 `media` 为 `[{"type":"first_frame","url":"https://example.com/start.png"},{"type":"last_frame","url":"https://example.com/end.png"}]`。参考生视频：使用 `reference_image`、`reference_video`、`reference_audio` 类型，可组合。编辑/延长：使用 `reference_video` 并在提示词说明意图；延长时 ratio 使用 adaptive。

素材限制：首尾帧不能与参考素材混用；file/link 二选一且必须开启提示词改写；参考图片最多10张，参考视频/音频各最多5个且各总长不超过15秒；输入视频总长+输出视频时长不得超过30秒。URL素材的格式、大小和时长由服务端校验。

### 官方协议参考

- [千问图像3.0](https://help.aliyun.com/zh/model-studio/qwen-image-generation-and-editing-api-reference)
- [万相视频3.0](https://help.aliyun.com/zh/model-studio/wan3-video-generation-api-reference)
- [万相视频编辑](https://help.aliyun.com/zh/model-studio/wan-video-editing-api-reference)

验证：`python -m unittest discover -s tests -v`。测试模拟HTTP响应，验证真实工具的请求与返回消息，不产生付费调用。实际生成需自行配置百炼凭据及开通对应地域模型。

一个强大的 Dify 插件，使用阿里云通义最新的万相、通义千问和 Z-Image 模型提供全面的 AI 图像和视频生成功能。支持文生图、文生视频、图生图、图生视频、图像翻译等多种生成模式，具有专业级质量和灵活的配置选项。

## 版本信息

- **当前版本**: v0.0.4
- **发布日期**: 2026-07-05
- **兼容性**: Dify 插件框架
- **Python 版本**: 3.12

### 版本历史
- **v0.0.4** (2026-07-05):
  - 新增 **HappyHorse 1.1** 模型应用于所有 HappyHorse 视频生成工具
  - 默认模型更新为 happyhorse-1.1 系列
  - 可用的 happyhorse-1.1 模型：happyhorse-1.1-t2v、happyhorse-1.1-i2v、happyhorse-1.1-r2v
- **v0.0.3** (2026-04-26):
  - 新增 **HappyHorse** 系列视频生成模型
  - 新增 HappyHorse 文生视频
  - 新增 HappyHorse 图生视频-基于首帧
  - 新增 HappyHorse 参考生视频
  - 新增 HappyHorse 视频编辑
- **v0.0.2** (2026-04-12): 
  - 新增 **视频续写** 工具 (wan_video_continue) - 使用 wan2.7-i2v 从现有片段继续生成视频
  - 新增 wan2.7-t2v 模型支持（文生视频）
  - 新增 wan2.7-i2v 模型支持（图生视频），支持多模态输入（首帧、首尾帧、视频续写）
  - 新增 wan2.7-r2v 模型支持（参考视频），增强功能
  - 新增 wan2.7-image-pro/wan2.7-image 模型支持（图生图），支持组图输出模式
  - 新增 **qwen-image2.0** 系列模型：qwen-image-2.0-pro、qwen-image-2.0、qwen-image-edit-max、qwen-image-edit-plus
  - 增强分辨率控制，wan2.7 模型新增 `resolution + ratio` 参数
  - 新增插件市场标签（productivity, image, videos）
- **v0.0.1** (2026-02-16): 初始版本，包含图像和视频生成功能

## 快速开始

1. 在您的 Dify 环境中安装插件
2. 配置阿里云 API 凭证（DashScope 的 API Key）
3. 开始使用 AI 生成图像和视频

## 核心特性
<img width="326" height="1141" alt="cn" src="https://github.com/user-attachments/assets/4f410524-c1f0-4146-b8b0-fe8f63e0ef64" /><img width="291" height="1210" alt="EN" src="https://github.com/user-attachments/assets/fe507baa-51d3-457b-9f38-affd8a9f573a" />

- **多种生成模式**: 文生图、文生视频、图生图、图生视频、图像翻译
- **最新 AI 模型**: 支持图像生成使用 wan2.7、qwen-image2.0、Z-image、wan2.6、wan2.5、wan2.2；视频生成使用 wan2.7-t2v、wan2.6-t2v、wan2.5-t2v-preview、wan2.2-t2v-plus
- **灵活的图像尺寸**: 多种宽高比，从 1:1 到 21:9，支持多种分辨率
- **视频生成**: 创建可自定义时长（2-15秒）的视频，支持同步音频生成
- **图像翻译**: AI 驱动的 OCR 和翻译功能（支持14+种语言）
- **首尾帧视频**: 从首帧和尾帧图像生成视频
- **参考视频**: 基于参考视频风格生成视频
- **视频续写**: 基于首段视频进行续写（wan2.7-i2v）
- **批量生成**: 单次请求生成多张图像（最多6张）
- **水印控制**: 可选水印，确保内容真实性

## 核心功能

### 图像生成

#### 万相文生图 (wan_text_2_image)
使用万相模型根据文本描述生成图像。
- **支持模型**: wan2.7-image-pro, wan2.7-image, wan2.6-t2i
- **功能特性**:
  - 多种宽高比（1:1、3:2、2:3、16:9、9:16）
  - 高分辨率输出（wan2.7-image-pro 最高支持 4K）
  - 可选水印
  - wan2.7 组图输出模式
  - wan2.7 思考模式增强推理
  - 提示词智能改写
  - 批量生成（1-4张，wan2.7 组图模式最高12张）
  - 反向提示词支持

#### 万相图生图 (wan_image_2_image)
使用万相模型根据文本和参考图像生成图像。
- **支持模型**: wan2.7-image-pro、wan2.7-image、wan2.6-image（兼容保留）
- **功能特性**:
  - 参考图像引导生成（1-9张）
  - 多种宽高比（1:1、2:3、3:2、3:4、4:3、9:16、16:9、21:9）
  - 支持 wan2.7 的 1K/2K 规格
  - 可选水印
  - wan2.7 组图输出模式
  - 图文混排输出模式（wan2.6兼容）
  - 提示词智能改写
  - 批量生成（1-4张，wan2.7组图模式最高12张）

#### 通义千问文生图 (qwen_text_2_image)
使用通义千问图像模型生成图像。
- **支持模型**: qwen-image-2.0-pro, qwen-image-2.0, qwen-image-2.0-pro-2026-03-03, qwen-image-2.0-2026-03-03, qwen-image-max, qwen-image-plus, qwen-image
- **功能特性**:
  - 高质量图像生成
  - 多种宽高比（16:9、4:3、1:1、3:4、9:16）
  - 可选水印
  - 提示词智能改写
  - 反向提示词支持
  - 随机种子可复现

#### 通义千问图生图 (qwen_image_2_image)
使用通义千问模型根据文本和参考图像生成图像。
- **支持模型**: qwen-image-2.0-pro, qwen-image-2.0, qwen-image-edit-max, qwen-image-edit-max-2026-01-16, qwen-image-edit-plus, qwen-image-edit, qwen-image-edit-plus-2025-10-30
- **功能特性**:
  - 参考图像引导生成（1-3张）
  - 多种宽高比（1:1、2:3、3:2、3:4、4:3、9:16、16:9、21:9）
  - 可选水印
  - 提示词智能改写
  - 批量生成（1-6张）
  - 高分辨率输出（最高 2048*872）

#### Z-Image 文生图 (z_image_text_2_image)
使用 Z-Image Turbo 模型生成图像。
- **支持模型**: z-image-turbo
- **功能特性**:
  - 快速图像生成
  - 丰富的宽高比支持（1:1、2:3、3:2、3:4、4:3、7:9、9:7、9:16、9:21、16:9、21:9）
  - 多种分辨率选项（1024 到 2048 像素）
  - 提示词智能改写
  - 随机种子可复现

#### 图像翻译 (qwen_image_translate)
AI 驱动的 OCR 和翻译功能，翻译图像中的文字。
- **支持模型**: qwen-mt-image
- **功能特性**:
  - 自动文字检测
  - 多语言翻译（14种语言）
  - 支持语言：中文、英文、日语、韩语、法语、德语、西班牙语、俄语、意大利语、葡萄牙语、阿拉伯语、泰语、越南语、印尼语
  - 领域提示提升翻译效果
  - 敏感词过滤
  - 术语表支持

### 视频生成

#### 文生视频 (wan_text_2_video)
使用万相模型根据文本描述生成视频。
- **支持模型**: wan2.7-t2v, wan2.6-t2v, wan2.5-t2v-preview, wan2.2-t2v-plus, wanx2.1-t2v-turbo, wanx2.1-t2v-plus
- **功能特性**:
  - 时长：2-15 秒（因模型而异）
  - 分辨率控制：wan2.7 使用 `resolution + ratio`，wan2.6 及更早模型使用 `size`
  - 同步音频生成
  - 提示词智能改写
  - 单镜头/多镜头支持（wan2.6 用 `shot_type`，wan2.7 通过 prompt 描述）
  - 自定义音频 URL
  - 反向提示词支持

#### 图生视频 (wan_first_image_2_video)
根据单张图像和文本描述生成视频。
- **支持模型**: wan2.7-i2v, wan2.6-i2v, wan2.5-i2v-preview, wan2.2-i2v-flash, wan2.2-i2v-plus, wanx2.1-i2v-turbo, wanx2.1-i2v-plus
- **功能特性**:
  - wan2.7-i2v 支持多模态输入：首帧、首尾帧、视频续写
  - 早期模型支持单图首帧输入
  - 时长：2-15 秒（因模型而异）
  - 分辨率：480P、720P、1080P
  - 同步音频生成
  - 视频特效模板
  - 提示词智能改写
  - 单镜头/多镜头支持

#### 首尾帧图生视频 (wan_first_end_image_2_video)
根据首帧和尾帧图像生成视频。
- **支持模型**: wan2.2-kf2v-flash
- **功能特性**:
  - 首帧和尾帧输入
  - 平滑过渡生成
  - 分辨率：480P、720P、1080P
  - 视频特效模板
  - 提示词智能改写

#### 参考视频 (wan_reference_video)
基于参考视频风格生成视频。
- **支持模型**: wan2.7-r2v, wan2.6-r2v, wan2.6-r2v-flash
- **功能特性**:
  - 多模态参考输入（图片/视频，最多5个）
  - 支持首帧图与参考音色（wan2.7-r2v）
  - 时长：2-10 秒（wan2.7 无参考视频时可到15秒）
  - 分辨率：720P 或 1080P（多种宽高比）
  - 同步音频生成（仅 wan2.6-r2v-flash 支持）
  - 单镜头/多镜头支持
  - 提示词智能改写

#### 视频续写 (wan_video_continue)
基于首段视频续写后续内容。
- **支持模型**: wan2.7-i2v
- **功能特性**:
  - 支持 `first_clip` 和 `first_clip + last_frame`
  - 时长 2-15 秒，分辨率 720P/1080P
  - 提示词智能改写和水印控制

#### 视频结果查询 (wan_video_query)
查询视频生成任务的状态和结果。
- **功能特性**:
  - 实时任务状态
  - 视频下载 URL 获取
  - 可选自动下载视频

#### 图片翻译结果查询 (qwen_image_translate_query)
查询图片翻译任务状态和结果。
- **功能特性**:
  - 实时任务状态
  - 翻译后图片获取

## 技术优势

- **最新 AI 模型**: 访问阿里云最新的万相、通义千问和 Z-Image 模型
- **高质量输出**: 专业级图像和视频生成
- **灵活配置**: 丰富的参数选项用于精细调整
- **异步处理**: 基于任务的高效视频生成工作流
- **多格式支持**: 支持各种图像和视频格式
- **音频生成**: 视频自动同步音频
- **批量处理**: 高效生成多张图像
- **图像翻译**: AI 驱动的图像文字翻译（14+种语言）

## 系统要求

- Python 3.12
- Dify 平台访问权限
- 阿里云 API 凭证（DashScope 的 API Key）
- 所需的 Python 包（通过 requirements.txt 安装）:
  - dify_plugin>=0.2.0
  - requests>=2.31.0,<3.0.0
  - pillow>=10.0.0,<11.0.0

## 安装与配置

1. 安装所需的依赖项：
   ```bash
   pip install -r requirements.txt
   ```

2. 在插件设置中配置阿里云 API 凭证：
   - **API Key**: 您的阿里云 DashScope API 密钥

3. 在您的 Dify 环境中安装插件

## 使用方法

### 图像生成工具

#### 1. 万相文生图
根据文本描述生成图像。
- **参数**:
  - `model`: 模型版本（默认：wan2.7-image-pro）
  - `prompt`: 图像的文本描述（必需，wan2.7 <=5000字符，wan2.6 <=2100字符）
  - `negative_prompt`: 描述不希望出现的内容（<=500字符，wan2.6兼容参数）
  - `size`: 图像尺寸（默认：2K，支持 1K/2K/4K 或具体分辨率如 1024*1024）
  - `n`: 生成图像数量（1-4；wan2.7 组图模式最高12）
  - `enable_sequential`: 启用 wan2.7 组图输出（默认：禁用）
  - `thinking_mode`: 启用 wan2.7 思考模式增强推理（默认：启用）
  - `prompt_extend`: 启用提示词智能改写（默认：启用）
  - `watermark`: 启用/禁用水印（默认：启用）
  - `seed`: 随机种子可复现

#### 2. 万相图生图
根据文本和参考图像生成图像。
- **参数**:
  - `model`: 模型版本（默认：wan2.7-image-pro）
  - `prompt`: 文本描述（必需，<=5000字符）
  - `images`: 参考图片文件（1-9张，必需）
  - `size`: 图像尺寸（默认：2K）
  - `n`: 生成图像数量（1-4；wan2.7开启组图时最高12）
  - `enable_sequential`: 启用 wan2.7 组图输出（默认：禁用）
  - `enable_interleave`: 启用图文混排输出（默认：禁用）
  - `prompt_extend`: 启用提示词智能改写（默认：启用）
  - `watermark`: 启用/禁用水印（默认：启用）

#### 3. 通义千问文生图
使用通义千问模型生成图像。
- **参数**:
  - `prompt`: 文本描述（必需）
  - `model`: 模型版本（默认：qwen-image-2.0-pro）
  - `size`: 图像尺寸（默认：1664*928）
  - `negative_prompt`: 描述不希望出现的内容
  - `prompt_extend`: 启用提示词智能改写
  - `watermark`: 启用/禁用水印（默认：启用）
  - `seed`: 随机种子可复现

#### 4. 通义千问图生图
使用通义千问模型根据文本和参考图像生成图像。
- **参数**:
  - `prompt`: 文本描述（必需）
  - `images`: 参考图片文件（1-3张，必需）
  - `model`: 模型版本（默认：qwen-image-2.0-pro）
  - `size`: 图像尺寸（默认：1024*1024）
  - `n`: 生成图像数量（1-6，默认：3）
  - `prompt_extend`: 启用提示词智能改写
  - `watermark`: 启用/禁用水印（默认：启用）

#### 5. Z-Image 文生图
使用 Z-Image Turbo 生成图像。
- **参数**:
  - `prompt`: 文本描述（必需，<=800字符）
  - `model`: 模型版本（默认：z-image-turbo）
  - `size`: 图像尺寸（默认：1024*1536）
  - `prompt_extend`: 启用提示词智能改写（默认：禁用）
  - `seed`: 随机种子可复现

#### 6. 图像翻译
翻译图像中的文字。
- **参数**:
  - `image_url`: 图片 URL（必需）
  - `target_lang`: 目标语言（必需）
  - `source_lang`: 源语言（默认：自动检测）
  - `domain_hint`: 领域提示提升翻译效果
  - `sensitives`: 敏感词（JSON数组）
  - `terminologies`: 术语表（JSON数组）
  - `model`: 模型版本（默认：qwen-mt-image）

### 视频生成工具

#### 7. 文生视频
根据文本描述生成视频。
- **参数**:
  - `model`: 模型版本（默认：wan2.6-t2v）
  - `prompt`: 文本描述（必需）
  - `negative_prompt`: 描述不希望出现的内容
  - `size`: 视频分辨率（默认：1920*1080）
  - `duration`: 时长（秒）（因模型而异，默认：5）
  - `audio_url`: 自定义音频文件 URL
  - `audio`: 自动生成音频（默认：启用）
  - `shot_type`: 单镜头或多镜头（默认：单镜头）
  - `prompt_extend`: 启用提示词智能改写（默认：启用）
  - `watermark`: 启用/禁用水印（默认：启用）
  - `seed`: 随机种子可复现

#### 8. 图生视频
根据图像生成视频，或基于首段视频进行续写。
- **参数**:
  - `model`: 模型版本（默认：wan2.6-i2v，支持 wan2.7-i2v）
  - `prompt`: 文本描述
  - `image_input` / `img_url`: 首帧图像输入
  - `last_frame_input` / `last_frame_url`: 可选尾帧图像（wan2.7-i2v）
  - `first_clip_url`: 可选首段视频 URL（wan2.7-i2v 续写）
  - `resolution`: 视频分辨率（默认：1080P）
  - `duration`: 时长（秒）（因模型而异，默认：5）
  - `template`: 视频特效模板
  - `audio_url`: 自定义音频文件 URL（wan2.7-i2v 仅首帧模式可用）
  - `audio`: 自动生成音频（默认：启用）
  - `shot_type`: 单镜头或多镜头（默认：单镜头）
  - `prompt_extend`: 启用提示词智能改写（默认：启用）
  - `watermark`: 启用/禁用水印（默认：启用）

#### 9. 首尾帧图生视频
根据首帧和尾帧图像生成视频。
- **参数**:
  - `model`: 模型版本（默认：wan2.2-kf2v-flash）
  - `prompt`: 文本描述
  - `first_frame_image`: 首帧图像（必需）
  - `last_frame_image`: 尾帧图像
  - `resolution`: 视频分辨率（默认：720P）
  - `template`: 视频特效模板
  - `prompt_extend`: 启用提示词智能改写（默认：启用）
  - `watermark`: 启用/禁用水印（默认：启用）

#### 10. 参考视频
基于参考视频风格生成视频。
- **参数**:
  - `model`: 模型版本（默认：wan2.7-r2v）
  - `prompt`: 文本描述（必需，wan2.7 最多5000字符 / wan2.6 最多1500字符）
  - `reference_urls`: 参考 URL（视频或图片，用分号分隔，最多5个）
  - `first_frame_image`: 可选首帧图像 URL（wan2.7-r2v）
  - `reference_voice`: 可选参考音色 URL（wan2.7-r2v）
  - `size`: 传统分辨率（宽*高，wan2.6 使用；wan2.7 兼容映射）
  - `resolution` / `ratio`: wan2.7 原生分辨率档位与宽高比
  - `duration`: 时长（秒）（wan2.6: 2-10；wan2.7: 2-10，若无参考视频可到15）
  - `shot_type`: 单镜头或多镜头（wan2.6）
  - `audio`: 自动生成音频（默认：启用，仅 wan2.6-r2v-flash 支持）
  - `prompt_extend`: 启用提示词智能改写（默认：启用）
  - `watermark`: 启用/禁用水印（默认：启用）

#### 11. 视频结果查询
查询视频生成任务状态。
- **参数**:
  - `task_id`: 视频生成任务 ID（必需）
  - `download_video`: 当视频可用时下载（默认：禁用）

#### 12. 图片翻译结果查询
查询图片翻译任务状态。
- **参数**:
  - `task_id`: 翻译任务 ID（必需）

#### 13. HappyHorse 文生视频
使用 HappyHorse 模型从文本生成视频。
- **参数**:
  - `model`: 模型版本（默认：happyhorse-1.1-t2v）
  - `prompt`: 视频生成的文本描述（必需）
  - `resolution`: 视频分辨率 - 720P 或 1080P（默认：1080P）
  - `ratio`: 宽高比 - 16:9, 9:16, 1:1, 4:3, 3:4（默认：16:9）
  - `duration`: 视频时长（秒），取值范围[3, 15]（默认：5）
  - `watermark`: 启用/禁用水印（默认：启用）
  - `seed`: 随机种子可复现

#### 14. HappyHorse 图生视频-基于首帧
使用 HappyHorse 模型从图像生成视频。
- **参数**:
  - `model`: 模型版本（默认：happyhorse-1.1-i2v）
  - `prompt`: 视频生成的文本描述（可选）
  - `image_input`: 首帧图片文件（可选）
  - `resolution`: 视频分辨率 - 720P 或 1080P（默认：1080P）
  - `duration`: 视频时长（秒），取值范围[3, 15]（默认：5）
  - `watermark`: 启用/禁用水印（默认：启用）
  - `seed`: 随机种子可复现

#### 15. HappyHorse 参考生视频
使用 HappyHorse 模型从多张参考图生成视频。
- **参数**:
  - `model`: 模型版本（默认：happyhorse-1.1-r2v）
  - `prompt`: 视频生成的文本描述（必需）
  - `files`: 参考图片文件（1-9张，必需）
  - `resolution`: 视频分辨率 - 720P 或 1080P（默认：1080P）
  - `ratio`: 宽高比 - 16:9, 9:16, 3:4, 4:3, 1:1（默认：16:9）
  - `duration`: 视频时长（秒），取值范围[3, 15]（默认：5）
  - `watermark`: 启用/禁用水印（默认：启用）
  - `seed`: 随机种子可复现

#### 16. HappyHorse 视频编辑
使用 HappyHorse 模型并结合可选参考图进行视频编辑。
- **参数**:
  - `model`: 模型版本（默认：happyhorse-1.0-video-edit）
  - `prompt`: 视频编辑的文本指令（必需）
  - `video_url`: 输入视频的公开链接（必需）
  - `files`: 可选参考图片文件（1-5张）
  - `resolution`: 视频分辨率 - 720P 或 1080P（默认：1080P）
  - `watermark`: 启用/禁用水印（默认：启用）
  - `audio_setting`: 音频处理模式 - auto 或 origin（默认：auto）
  - `seed`: 随机种子可复现

#### 17. 视频续写
使用 wan2.7-i2v 模型基于首段视频进行续写。
- **参数**:
  - `model`: 模型版本（默认：wan2.7-i2v）
  - `prompt`: 描述视频如何继续生成（可选，最多5000字符）
  - `negative_prompt`: 描述不希望出现的内容（可选，最多500字符）
  - `first_clip_input`: 首段视频文件（mp4/mov，建议2-10秒）
  - `first_clip_url`: 首段视频链接（http/https/oss）
  - `last_frame_input`: 尾帧图片文件（可选）
  - `last_frame_url`: 尾帧图片链接（可选）
  - `resolution`: 视频分辨率（默认：1080P）
  - `duration`: 视频时长（秒），取值范围[2, 15]（默认：5）
  - `watermark`: 启用/禁用水印（默认：启用）
  - `seed`: 随机种子可复现

## 注意事项

- 视频生成是异步的，使用视频查询工具检查状态并获取结果
- 图片翻译是异步的，使用图片翻译查询工具检查状态
- 时长限制因模型而异（参见工具描述中的模型文档）
- 参考图像大小应在 10MB 以内
- 水印默认启用以确保内容真实性
- 提示词智能改写默认启用以获得更好的效果

## 开发者信息

- **作者**: `https://github.com/sawyer-shi`
- **邮箱**: sawyer36@foxmail.com
- **许可证**: Apache License 2.0
- **源代码**: `https://github.com/sawyer-shi/dify-plugins-tongyi_aigc`
- **支持**: 通过 Dify 平台和 GitHub Issues 提供

## 许可证声明

本项目采用 Apache License 2.0 许可证。完整的许可证文本请参阅 [LICENSE](LICENSE) 文件。

---

**准备好使用 AI 创建精美的图像和视频了吗？**
