# Steam 创意工坊上传与更新

## 已核实的官方入口

核实日期：2026-10-29。Mega Crit 官方工具是 [megacrit/sts2-mod-uploader](https://github.com/megacrit/sts2-mod-uploader)，不是 STS1 的上传器。官方 [v0.2.0 Release](https://github.com/megacrit/sts2-mod-uploader/releases/tag/v0.2.0) 提供 macOS ARM64／x64、Windows ARM64／x64 和 Linux x64；本机已运行 osx-arm64 的 `--help`、`upload --help` 与 `new -w`。这些检查没有调用 Steam 上传。

再次使用时读取当前 [README](https://github.com/megacrit/sts2-mod-uploader/blob/main/README.md)、[工作区说明](https://github.com/megacrit/sts2-mod-uploader/blob/main/template/README.md) 与实际下载版本的模板。main 分支可能领先于 Release；字段行为以所用二进制对应 tag 和 `--help` 为准。

## 工作区结构

```text
MyModWorkspace/
  workshop.json
  image.png
  content/
    ExampleMod.json
    ExampleMod.dll
    ExampleMod.pck
    Native/...
    Licenses/...
  mod_id.txt          首次成功上传后由官方上传器写入
```

上传器上传 `content/` 的内容。manifest、DLL、PCK 直接放在该目录，原生库和许可保持相对路径；不要把发布 ZIP 直接放进 `content/`。`workshop.json` 是工坊元数据，游戏自身的 `ExampleMod.json` 是 Loader 清单，两者用途不同。

主预览必须名为 `image.png`、小于 1 MB。可选的 `previews/` 放额外预览；更新时其中缺失的旧文件可能被删除，而整个 `previews/` 不存在时通常保留现有预览。脚本默认不创建该目录。

## 准备工作区

可以由官方模板开始：

```sh
./ModUploader new -w /absolute/path/MyModWorkspace
```

或者从本 Skill 已校验的成品生成工作区：

```sh
python3 /path/to/skill/scripts/prepare_workshop.py \
  --package /path/to/ExampleMod-1.0.0-macos-arm64-release.zip \
  --workspace /path/to/MyModWorkspace \
  --preview /path/to/image.png \
  --dependency LibraryMod=1234567890 \
  --visibility private
```

`--dependency` 可重复；无运行前置时不用传。参数左边是 manifest 的 Mod ID，右边是 Steam 工坊条目的数字 ID。脚本要求每个 manifest 前置都有对应映射，并在 `content/` 写完后逐文件读回 SHA-256。

`workshop.json` 示例：

```json
{
  "title": "ExampleMod [macOS ARM64]",
  "description": "内容、最低游戏版本、平台、依赖和使用说明。",
  "visibility": "private",
  "changeNote": "1.0.0 首次交付。",
  "tags": [],
  "dependencies": [1234567890],
  "contentDescriptors": []
}
```

可见性支持 `private`、`public`、`unlisted`、`friends_only`。`dependencies` 使用数字工坊 ID，不能填 manifest 的文字 ID。`Tools & APIs` 标签只用于真正的工具／API Mod。版本分支 `minBranch`／`maxBranch` 的官方说明提示行为有差异，优先在网页确认设置；同时在描述中清楚写出实际测试的分支和版本。

## 执行上传

用户已选择 Steam 发布渠道、账号、条目／新建与可见性后，在上传器目录运行，保持附带的 Steam 原生库和 `steam_appid.txt`，Steam 客户端登录拥有游戏的账号：

```sh
./ModUploader upload -w /absolute/path/MyModWorkspace
```

Windows 使用 `ModUploader.exe`。新建条目时不要带 `--id`，且工作区没有 `mod_id.txt`；更新则保留该文件。也可以明确指定更新已有条目：

```sh
./ModUploader upload -w /absolute/path/MyModWorkspace --id 1234567890
```

首次提交可能要求账号本人接受 [Steam Workshop 协议](https://steamcommunity.com/sharedfiles/workshoplegalagreement)。遇到账号条款页面时交给账号持有人完成，再继续已授权的上传。

## 更新与失败处理

保留同一个工作区／`mod_id.txt`，更换为新版本完整 `content/`，更新 `changeNote`，重新核对依赖、平台和预览。不能遗留旧 DLL／原生库，也不要删除条目 ID 来“修复”网络问题，否则会建立重复条目。

读取 `mod-uploader.log`、结果 ID 和页面状态。上传器 v0.2.0 在成功流程的末尾才写入 `mod_id.txt`，因此超时或依赖操作报错时可能已有条目：先从日志／账号工坊列表找回条目并使用其 ID 继续，不能盲目新建。当前 main 对省略 `dependencies` 的处理曾有修复，使用旧 Release 更新时显式传递完整的依赖列表并从网页读回，避免清掉手工设置的 Required Items。

## 上传后的验收

1. 确认目标条目页面、账号、标题、可见性、更新时间、Required Items 和下载大小。
2. 订阅该条目，Steam 完成下载后比对全部运行文件 SHA-256，而非只看上传器退出码。
3. 在游戏正常退出时处理本地同 ID 副本，避免 Loader 同时找到本地版和工坊版；保留可回退副本。
4. 使用实际订阅文件启动，确认依赖、版本日志、原生扩展、模型／语音、目标流程；联机与重连需相应机器实测。

只有上传器成功及页面／下载内容读回完成，才记录“工坊已上传”。生成工作区和执行帮助命令只记录“发布准备完成”。
