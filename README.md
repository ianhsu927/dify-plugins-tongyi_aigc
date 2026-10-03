# TongYi AIGC

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

A powerful Dify plugin providing comprehensive AI-powered image and video generation capabilities using Alibaba Cloud Tongyi's latest Wanxiang, Qwen, and Z-Image models. Supports text-to-image, text-to-video, image-to-image, image-to-video, image translation, and more with professional-grade quality and flexible configuration options.

## Version Information

- **Current Version**: v0.0.4
- **Release Date**: 2026-07-05
- **Compatibility**: Dify Plugin Framework
- **Python Version**: 3.12

### Version History
- **v0.0.4** (2026-07-05):
  - Added **HappyHorse 1.1** model for all HappyHorse video generation tools
  - Updated default model to happyhorse-1.1 for all HappyHorse features
  - Available happyhorse-1.1 models: happyhorse-1.1-t2v, happyhorse-1.1-i2v, happyhorse-1.1-r2v
- **v0.0.3** (2026-04-26):
  - Added **HappyHorse** series models for video generation
  - Added HappyHorse Text to Video
  - Added HappyHorse Image to Video - First Frame
  - Added HappyHorse Reference Video 
  - Added HappyHorse Video Editing 
- **v0.0.2** (2026-04-12): 
  - Added new **Video Continuation** tool (wan_video_continue) - Continue video from existing clips using wan2.7-i2v
  - Added wan2.7-t2v model support for Text to Video
  - Added wan2.7-i2v model support for Image to Video with multi-modal inputs (first-frame, first+last frame, video continuation)
  - Added wan2.7-r2v model support for Reference Video with enhanced features
  - Added wan2.7-image-pro/wan2.7-image models for Image to Image with sequential grouped output mode
  - Added **qwen-image2.0** series models: qwen-image-2.0-pro, qwen-image-2.0, qwen-image-edit-max, qwen-image-edit-plus
  - Enhanced resolution control with new `resolution + ratio` parameters for wan2.7 models
  - Added tags for plugin marketplace (productivity, image, videos)
- **v0.0.1** (2026-02-16): Initial release with image and video generation capabilities

## Quick Start

1. Install the plugin in your Dify environment
2. Configure your Alibaba Cloud API credentials (API Key from DashScope)
3. Start generating images and videos with AI

## Key Features
<img width="326" height="1141" alt="cn" src="https://github.com/user-attachments/assets/4f410524-c1f0-4146-b8b0-fe8f63e0ef64" /><img width="291" height="1210" alt="EN" src="https://github.com/user-attachments/assets/fe507baa-51d3-457b-9f38-affd8a9f573a" />



- **Multiple Generation Modes**: Text-to-image, text-to-video, image-to-image, image-to-video, image translation
- **Latest AI Models**: Supports wan2.7, qwen-image2.0, Z-image, wan2.6, wan2.5, wan2.2 for images; wan2.7-t2v, wan2.6-t2v, wan2.5-t2v-preview, wan2.2-t2v-plus for videos
- **Flexible Image Sizes**: Multiple aspect ratios from 1:1 to 21:9 with various resolutions
- **Video Generation**: Create videos with customizable duration (2-15 seconds) and synchronized audio
- **Image Translation**: Translate text in images with AI-powered OCR and translation (14+ languages)
- **First-Last Frame Video**: Create videos from first and last frame images
- **Reference Video**: Generate videos based on reference video style
- **Video Continuation**: Continue existing clips with wan2.7-i2v
- **Batch Generation**: Generate multiple images in a single request (up to 6 images)
- **Watermark Control**: Optional watermark for content authenticity

## Core Features

### Image Generation

#### Wan Text to Image (wan_text_2_image)
Generate images from text descriptions using Wanxiang models.
- **Supported Models**: wan2.7-image-pro, wan2.7-image, wan2.6-t2i
- **Features**:
  - Multiple aspect ratios (1:1, 3:2, 2:3, 16:9, 9:16)
  - High resolution output (up to 4K for wan2.7-image-pro)
  - Optional watermark
  - Sequential grouped image output mode (wan2.7)
  - Thinking mode for enhanced reasoning (wan2.7)
  - Prompt intelligent rewriting
  - Batch generation (1-4 images; up to 12 in wan2.7 sequential mode)
  - Negative prompt support

#### Wan Image to Image (wan_image_2_image)
Generate images from text and reference images using Wanxiang models.
- **Supported Models**: wan2.7-image-pro, wan2.7-image, wan2.6-image (compatibility)
- **Features**:
  - Reference image guided generation (1-9 images)
  - Multiple aspect ratios (1:1, 2:3, 3:2, 3:4, 4:3, 9:16, 16:9, 21:9)
  - 1K/2K presets for wan2.7 models
  - Optional watermark
  - Sequential grouped image output mode (wan2.7)
  - Interleaved text and image output mode (wan2.6 compatibility)
  - Prompt intelligent rewriting
  - Batch generation (1-4 images; up to 12 in wan2.7 sequential mode)

#### Qwen Text to Image (qwen_text_2_image)
Generate images using Qwen image models.
- **Supported Models**: qwen-image-2.0-pro, qwen-image-2.0, qwen-image-2.0-pro-2026-03-03, qwen-image-2.0-2026-03-03, qwen-image-max, qwen-image-plus, qwen-image
- **Features**:
  - High quality image generation
  - Multiple aspect ratios (16:9, 4:3, 1:1, 3:4, 9:16)
  - Optional watermark
  - Prompt intelligent rewriting
  - Negative prompt support
  - Random seed for reproducibility

#### Qwen Image to Image (qwen_image_2_image)
Generate images from text and reference images using Qwen models.
- **Supported Models**: qwen-image-2.0-pro, qwen-image-2.0, qwen-image-edit-max, qwen-image-edit-max-2026-01-16, qwen-image-edit-plus, qwen-image-edit, qwen-image-edit-plus-2025-10-30
- **Features**:
  - Reference image guided generation (1-3 images)
  - Multiple aspect ratios (1:1, 2:3, 3:2, 3:4, 4:3, 9:16, 16:9, 21:9)
  - Optional watermark
  - Prompt intelligent rewriting
  - Batch generation (1-6 images)
  - High resolution output (up to 2048*872)

#### Z-Image Text to Image (z_image_text_2_image)
Generate images using Z-Image Turbo model.
- **Supported Models**: z-image-turbo
- **Features**:
  - Fast image generation
  - Extensive aspect ratio support (1:1, 2:3, 3:2, 3:4, 4:3, 7:9, 9:7, 9:16, 9:21, 16:9, 21:9)
  - Multiple resolution options (1024 to 2048 pixels)
  - Prompt intelligent rewriting
  - Random seed for reproducibility

#### Image Translation (qwen_image_translate)
Translate text in images with AI-powered OCR and translation.
- **Supported Models**: qwen-mt-image
- **Features**:
  - Automatic text detection
  - Multi-language translation (14 languages)
  - Supported languages: Chinese, English, Japanese, Korean, French, German, Spanish, Russian, Italian, Portuguese, Arabic, Thai, Vietnamese, Indonesian
  - Domain hint for improved translation
  - Sensitive words filtering
  - Terminology support

### Video Generation

#### Text to Video (wan_text_2_video)
Generate videos from text descriptions using Wanxiang models.
- **Supported Models**: wan2.7-t2v, wan2.6-t2v, wan2.5-t2v-preview, wan2.2-t2v-plus, wanx2.1-t2v-turbo, wanx2.1-t2v-plus
- **Features**:
  - Duration: 2-15 seconds (model dependent)
  - Resolution control: `resolution + ratio` (wan2.7) or `size` (wan2.6 and earlier)
  - Synchronized audio generation
  - Prompt intelligent rewriting
  - Single/Multi shot support (shot_type for wan2.6, prompt-driven for wan2.7)
  - Custom audio URL support
  - Negative prompt support

#### Image to Video (wan_first_image_2_video)
Generate video from a single image with text description.
- **Supported Models**: wan2.7-i2v, wan2.6-i2v, wan2.5-i2v-preview, wan2.2-i2v-flash, wan2.2-i2v-plus, wanx2.1-i2v-turbo, wanx2.1-i2v-plus
- **Features**:
  - Multi-modal inputs on wan2.7-i2v: first-frame, first+last frame, or video continuation
  - Single image input as first frame (legacy models)
  - Duration: 2-15 seconds (model dependent)
  - Resolution: 480P, 720P, 1080P
  - Synchronized audio generation
  - Video effect templates
  - Prompt intelligent rewriting
  - Single/Multi shot support

#### First-Last Frame Video (wan_first_end_image_2_video)
Generate video from first and last frame images.
- **Supported Models**: wan2.2-kf2v-flash
- **Features**:
  - First and last frame input
  - Smooth transition generation
  - Resolution: 480P, 720P, 1080P
  - Video effect templates
  - Prompt intelligent rewriting

#### Reference Video (wan_reference_video)
Generate videos based on reference video style.
- **Supported Models**: wan2.7-r2v, wan2.6-r2v, wan2.6-r2v-flash
- **Features**:
  - Multi-modal references (images/videos) input (up to 5)
  - Optional first-frame and reference voice support (wan2.7-r2v)
  - Duration: 2-10 seconds (or up to 15s for wan2.7 without reference video)
  - Resolution: 720P or 1080P (multiple aspect ratios)
  - Synchronized audio generation (wan2.6-r2v-flash only)
  - Single/Multi shot support
  - Prompt intelligent rewriting

#### Video Continuation (wan_video_continue)
Continue a video from an existing first clip.
- **Supported Models**: wan2.7-i2v
- **Features**:
  - Supports `first_clip` and `first_clip + last_frame`
  - Duration 2-15 seconds and 720P/1080P resolution
  - Prompt intelligent rewriting and watermark control

#### Video Query (wan_video_query)
Query the status and results of video generation tasks.
- **Features**:
  - Real-time task status
  - Video download URL retrieval
  - Optional automatic video download

#### Image Translation Query (qwen_image_translate_query)
Query image translation task status and results.
- **Features**:
  - Real-time task status
  - Translated image retrieval

## Technical Advantages

- **Latest AI Models**: Access to Alibaba Cloud's newest Wanxiang, Qwen, and Z-Image models
- **High Quality Output**: Professional-grade image and video generation
- **Flexible Configuration**: Extensive parameter options for fine-tuning
- **Async Processing**: Efficient video generation with task-based workflow
- **Multi-Format Support**: Support for various image and video formats
- **Audio Generation**: Automatic synchronized audio for videos
- **Batch Processing**: Generate multiple images efficiently
- **Image Translation**: AI-powered text translation in images (14+ languages)

## Requirements

- Python 3.12
- Dify Platform access
- Alibaba Cloud API credentials (API Key from DashScope)
- Required Python packages (installed via requirements.txt):
  - dify_plugin>=0.2.0
  - requests>=2.31.0,<3.0.0
  - pillow>=10.0.0,<11.0.0

## Installation & Configuration

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure your Alibaba Cloud API credentials in the plugin settings:
   - **API Key**: Your Alibaba Cloud DashScope API key

3. Install the plugin in your Dify environment

## Usage

### Image Generation Tools

#### 1. Wan Text to Image
Generate images from text descriptions.
- **Parameters**:
  - `model`: Model version (default: wan2.7-image-pro)
  - `prompt`: Text description of the image (required, wan2.7 <=5000 chars, wan2.6 <=2100 chars)
  - `negative_prompt`: Describe what you don't want (<=500 chars, wan2.6 compatibility)
  - `size`: Image size (default: 2K, supports 1K/2K/4K or specific resolutions like 1024*1024)
  - `n`: Number of images to generate (1-4, up to 12 with wan2.7 sequential mode)
  - `enable_sequential`: Enable grouped image generation for wan2.7 (default: false)
  - `thinking_mode`: Enable thinking mode for enhanced reasoning on wan2.7 (default: true)
  - `prompt_extend`: Enable prompt intelligent rewriting (default: true)
  - `watermark`: Enable/disable watermark (default: true)
  - `seed`: Random seed for reproducibility

#### 2. Wan Image to Image
Generate images from text and reference images.
- **Parameters**:
  - `model`: Model version (default: wan2.7-image-pro)
  - `prompt`: Text description (required, <=5000 chars)
  - `images`: Reference image files (1-9 images, required)
  - `size`: Image size (default: 2K)
  - `n`: Number of images to generate (1-4, up to 12 when `enable_sequential=true` on wan2.7)
  - `enable_sequential`: Enable grouped image generation for wan2.7 (default: false)
  - `enable_interleave`: Enable interleaved output (default: false)
  - `prompt_extend`: Enable prompt intelligent rewriting (default: true)
  - `watermark`: Enable/disable watermark (default: true)

#### 3. Qwen Text to Image
Generate images using Qwen models.
- **Parameters**:
  - `prompt`: Text description (required)
  - `model`: Model version (default: qwen-image-2.0-pro)
  - `size`: Image size (default: 1664*928)
  - `negative_prompt`: Describe what you don't want
  - `prompt_extend`: Enable prompt intelligent rewriting
  - `watermark`: Enable/disable watermark (default: true)
  - `seed`: Random seed for reproducibility

#### 4. Qwen Image to Image
Generate images from text and reference images using Qwen models.
- **Parameters**:
  - `prompt`: Text description (required)
  - `images`: Reference image files (1-3 images, required)
  - `model`: Model version (default: qwen-image-2.0-pro)
  - `size`: Image size (default: 1024*1024)
  - `n`: Number of images to generate (1-6, default: 3)
  - `prompt_extend`: Enable prompt intelligent rewriting
  - `watermark`: Enable/disable watermark (default: true)

#### 5. Z-Image Text to Image
Generate images using Z-Image Turbo.
- **Parameters**:
  - `prompt`: Text description (required, <=800 chars)
  - `model`: Model version (default: z-image-turbo)
  - `size`: Image size (default: 1024*1536)
  - `prompt_extend`: Enable prompt intelligent rewriting (default: false)
  - `seed`: Random seed for reproducibility

#### 6. Image Translation
Translate text in images.
- **Parameters**:
  - `image_url`: Image URL for translation (required)
  - `target_lang`: Target language (required)
  - `source_lang`: Source language (default: auto)
  - `domain_hint`: Domain hint for improved translation
  - `sensitives`: Sensitive words (JSON array)
  - `terminologies`: Terminologies (JSON array)
  - `model`: Model version (default: qwen-mt-image)

### Video Generation Tools

#### 7. Text to Video
Generate videos from text descriptions.
- **Parameters**:
  - `model`: Model version (default: wan2.6-t2v)
  - `prompt`: Text description (required)
  - `negative_prompt`: Describe what you don't want
  - `size`: Video resolution (default: 1920*1080)
  - `duration`: Duration in seconds (model dependent, default: 5)
  - `audio_url`: Custom audio file URL
  - `audio`: Auto generate audio (default: true)
  - `shot_type`: Single or multi shot (default: single)
  - `prompt_extend`: Enable prompt intelligent rewriting (default: true)
  - `watermark`: Enable/disable watermark (default: true)
  - `seed`: Random seed for reproducibility

#### 8. Image to Video
Generate video from an image or continue from a video clip.
- **Parameters**:
  - `model`: Model version (default: wan2.6-i2v, supports wan2.7-i2v)
  - `prompt`: Text description
  - `image_input` / `img_url`: First frame image input
  - `last_frame_input` / `last_frame_url`: Optional last frame image (wan2.7-i2v)
  - `first_clip_url`: Optional first clip video URL for continuation (wan2.7-i2v)
  - `resolution`: Video resolution (default: 1080P)
  - `duration`: Duration in seconds (model dependent, default: 5)
  - `template`: Video effect template
  - `audio_url`: Custom audio file URL (wan2.7-i2v only in first-frame modes)
  - `audio`: Auto generate audio (default: true)
  - `shot_type`: Single or multi shot (default: single)
  - `prompt_extend`: Enable prompt intelligent rewriting (default: true)
  - `watermark`: Enable/disable watermark (default: true)

#### 9. First-Last Frame Video
Generate video from first and last frame images.
- **Parameters**:
  - `model`: Model version (default: wan2.2-kf2v-flash)
  - `prompt`: Text description
  - `first_frame_image`: First frame image (required)
  - `last_frame_image`: Last frame image
  - `resolution`: Video resolution (default: 720P)
  - `template`: Video effect template
  - `prompt_extend`: Enable prompt intelligent rewriting (default: true)
  - `watermark`: Enable/disable watermark (default: true)

#### 10. Reference Video
Generate videos based on reference video style.
- **Parameters**:
  - `model`: Model version (default: wan2.7-r2v)
  - `prompt`: Text description (required, wan2.7 max 5000 / wan2.6 max 1500)
  - `reference_urls`: Reference URLs (videos or images, semicolon-separated, max 5)
  - `first_frame_image`: Optional first frame image URL (wan2.7-r2v)
  - `reference_voice`: Optional reference voice URL (wan2.7-r2v)
  - `size`: Legacy resolution in `width*height` (wan2.6; also mapped for wan2.7 compatibility)
  - `resolution` / `ratio`: Native wan2.7 resolution tier and aspect ratio
  - `duration`: Duration in seconds (wan2.6: 2-10; wan2.7: 2-10 or up to 15 without reference video)
  - `shot_type`: Single or multi shot (wan2.6)
  - `audio`: Auto generate audio (default: true, wan2.6-r2v-flash only)
  - `prompt_extend`: Enable prompt intelligent rewriting (default: true)
  - `watermark`: Enable/disable watermark (default: true)

#### 11. Video Query
Query video generation task status.
- **Parameters**:
  - `task_id`: Video generation task ID (required)
  - `download_video`: Download video when available (default: false)

#### 12. Image Translation Query
Query image translation task status.
- **Parameters**:
  - `task_id`: Translation task ID (required)

#### 13. HappyHorse Text to Video
Generate videos from text using HappyHorse model.
- **Parameters**:
  - `model`: Model version (default: happyhorse-1.1-t2v)
  - `prompt`: Text description for video generation (required)
  - `resolution`: Video resolution - 720P or 1080P (default: 1080P)
  - `ratio`: Aspect ratio - 16:9, 9:16, 1:1, 4:3, 3:4 (default: 16:9)
  - `duration`: Video duration in seconds, range [3, 15] (default: 5)
  - `watermark`: Enable/disable watermark (default: true)
  - `seed`: Random seed for reproducibility

#### 14. HappyHorse Image to Video - First Frame
Generate videos from images using HappyHorse model.
- **Parameters**:
  - `model`: Model version (default: happyhorse-1.1-i2v)
  - `prompt`: Text description for video generation (optional)
  - `image_input`: First frame image file (optional)
  - `resolution`: Video resolution - 720P or 1080P (default: 1080P)
  - `duration`: Video duration in seconds, range [3, 15] (default: 5)
  - `watermark`: Enable/disable watermark (default: true)
  - `seed`: Random seed for reproducibility

#### 15. HappyHorse Reference Video
Generate videos from multiple reference images using HappyHorse model.
- **Parameters**:
  - `model`: Model version (default: happyhorse-1.1-r2v)
  - `prompt`: Text description for video generation (required)
  - `files`: Reference image files (1-9 images, required)
  - `resolution`: Video resolution - 720P or 1080P (default: 1080P)
  - `ratio`: Aspect ratio - 16:9, 9:16, 3:4, 4:3, 1:1 (default: 16:9)
  - `duration`: Video duration in seconds, range [3, 15] (default: 5)
  - `watermark`: Enable/disable watermark (default: true)
  - `seed`: Random seed for reproducibility

#### 16. HappyHorse Video Edit
Edit videos using HappyHorse model with optional reference images.
- **Parameters**:
  - `model`: Model version (default: happyhorse-1.0-video-edit)
  - `prompt`: Editing instruction for the video (required)
  - `video_url`: Public URL of the input video (required)
  - `files`: Optional reference image files (1-5 images)
  - `resolution`: Video resolution - 720P or 1080P (default: 1080P)
  - `watermark`: Enable/disable watermark (default: true)
  - `audio_setting`: Audio handling mode - auto or origin (default: auto)
  - `seed`: Random seed for reproducibility

#### 17. Video Continue
Continue videos from first clip using wan2.7-i2v model.
- **Parameters**:
  - `model`: Model version (default: wan2.7-i2v)
  - `prompt`: Describe how the video should continue (optional, max 5000 chars)
  - `negative_prompt`: Describe what should not appear (optional, max 500 chars)
  - `first_clip_input`: First clip file (mp4/mov, 2-10s recommended)
  - `first_clip_url`: First clip URL (http/https/oss)
  - `last_frame_input`: Last frame image file (optional)
  - `last_frame_url`: Last frame image URL (optional)
  - `resolution`: Video resolution (default: 1080P)
  - `duration`: Video duration in seconds, range [2, 15] (default: 5)
  - `watermark`: Enable/disable watermark (default: true)
  - `seed`: Random seed for reproducibility

## Notes

- Video generation is asynchronous; use Video Query to check status and retrieve results
- Image translation is asynchronous; use Image Translation Query to check status
- Duration limits vary by model (see model documentation in tool descriptions)
- Reference images should be under 10MB in size
- Watermark is enabled by default for content authenticity
- Prompt intelligent rewriting is enabled by default for better results

## Developer Information

- **Author**: `https://github.com/sawyer-shi`
- **Email**: sawyer36@foxmail.com
- **License**: Apache License 2.0
- **Source Code**: `https://github.com/sawyer-shi/dify-plugins-tongyi_aigc`
- **Support**: Through Dify platform and GitHub Issues

## License Notice

This project is licensed under Apache License 2.0. See [LICENSE](LICENSE) file for full license text.

---

**Ready to create stunning images and videos with AI?**
