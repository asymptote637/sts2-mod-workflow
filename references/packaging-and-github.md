# 打包、安装与 GitHub 发布

## 使用验收过的输入

核对源码 manifest、程序集版本、构建报告和验收版本。`package_mod.py` 使用以下报告形状：

```json
{"files":{"ExampleMod.json":"64位小写SHA-256","ExampleMod.dll":"64位小写SHA-256"}}
```

```json
{"version":"1.0.0","passed":true,"artifacts":{"ExampleMod.json":"同一SHA-256","ExampleMod.dll":"同一SHA-256"}}
```

示例 SHA 字符串仅解释格式，实际必须来自文件和真实测试。脚本检查 `passed`、版本、完整哈希映射和所有实际文件；路径逃逸、符号链接、旧验收或重复 ZIP 条目会报错。不同项目的报告可做小型适配，保留原始证据指针。

根据平台原生库标记包名。包含 `.dylib`／macOS framework 的包不能直接改名为 Windows 包；Windows 还需自己的 Cubism、Core 和其他运行依赖。PCK 内可能引用外部原生扩展，也要核对这些文件。

## 成品 ZIP

先编写针对当前版本的安装说明，包含游戏最低版本／分支、CPU／系统、运行前置、拷贝位置、启用方式、冲突处理和回退。将该文件传给脚本：

```sh
python3 /path/to/skill/scripts/package_mod.py \
  --project /path/to/project --mod-id ExampleMod --platform macos-arm64 \
  --build /path/to/project/dist/build.json \
  --acceptance /path/to/project/work/acceptance-1.0.0.json \
  --install-notes /path/to/INSTALL.md \
  --output /path/to/output/ExampleMod-1.0.0-macos-arm64-release.zip
```

输出为 ZIP、同名 `.manifest.json` 和 `.sha256`。ZIP 内将运行文件放在 `ExampleMod/`，说明与校验放在 `RELEASE/`，不会将整个开发目录打包。

目录中的未列入清单文件只在元数据中记录为排除项，保持原文件原样。新平台、更新依赖或源码变化需要新验收；仅补入安装说明的重新包装保留 DLL／PCK 原哈希。

已有只含已验收运行文件的 ZIP 时可加 `--reuse-zip <old.zip>`；输入 ZIP 的精确成员集和 SHA-256 必须通过检查。正式输出生成后不覆盖同名旧包。验证命令：

```sh
python3 /path/to/skill/scripts/package_mod.py --verify /path/to/output/ExampleMod-1.0.0-macos-arm64-release.zip
```

ZIP 内自带的哈希用于检查文件一致性。外部 `.sha256` 或 GitHub 返回的资产 digest 用于将下载结果绑定到已发布的包，不能只相信任意未知 ZIP 自带的声明。

## 安装与回退

使用项目原有安装器；不因“打包”任务而自动改动游戏安装。手动安装时先正常退出游戏，备份旧 Mod 目录和本次会修改的设置，再替换整个 Mod 目录，避免遗留旧文件。

本机 macOS 示例安装位置为 Steam 游戏应用的 `Contents/MacOS/mods/<ModID>/`。Windows／Linux 从实际启动程序和当前 Loader 查找路径确认，通常是启动程序旁的 `mods/<ModID>/`。不要猜测 app bundle 或依赖资源路径。

RitsuLib 等外部依赖单独订阅；不把其工坊文件随意合进成品。内置模板与外置依赖分开描述，明确哪些原 Mod 应禁用。安装读回检查 DLL、PCK、manifest、原生库和许可的 SHA-256，原生存档及外观快照另做前后清单比较。

## GitHub 仓库与 Release

优先使用已连接的 GitHub 工具读取仓库。需要创建仓库和上传二进制 Release、连接器未提供相应入口时使用 `gh`。先核对登录账号、同名仓库与可见性；用户已指定公开／私有时直接遵循。

大 Mod ZIP 放 Release 资产，不放普通 Git 历史。GitHub 对普通 Git 大文件和 Release 资产的限制不同，操作前查 [大文件限制](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github) 与 [Release 分发](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)。截至 2026-10-29 单个 Release 资产限制为 2 GiB；超过时设计拆包／其他分发渠道，不能反复推入普通 Git。

建议仓库只提交使用说明、版本摘要、哈希清单；公开 Skill 仓库提交 Skill、本身的脚本和方法文档，素材包按用户指定单独保存。确认目标目录不是用户已有无关仓库，再做初始化：

```sh
git init -b main /path/to/release-repo
git -C /path/to/release-repo add README.md release-manifest.json SHA256SUMS
git -C /path/to/release-repo commit -m 'chore(release): prepare accepted mod package'
gh repo create OWNER/REPOSITORY --private --source /path/to/release-repo --remote origin --push
gh release create v1.0.0 \
  /path/to/ExampleMod-1.0.0-macos-arm64-release.zip \
  /path/to/ExampleMod-1.0.0-macos-arm64-release.sha256 \
  --repo OWNER/REPOSITORY --title 'ExampleMod 1.0.0 · macOS ARM64' \
  --notes-file /path/to/release-notes.md --draft
```

Release 说明用文件保留真实换行。首次上传可以暂存为 draft，资产核对完成后按已授权范围发布：

```sh
gh api repos/OWNER/REPOSITORY/releases/tags/v1.0.0 \
  --jq '{html_url,draft,assets:[.assets[]|{name,size,state,digest}]}'
gh release edit v1.0.0 --repo OWNER/REPOSITORY --draft=false
gh repo view OWNER/REPOSITORY --json visibility,url
```

若 draft 的 tag 查找接口未返回条目，使用 `gh release view` 获取内部 ID，再查询对应 release；不要因不可见而创建第二份。

对每个资产核对名称、字节数和 GitHub `sha256:` digest。若后端没有 digest，将资产下载到新的临时目录并计算 SHA-256。公开 Skill 的文本也读回一个实际 commit 文件或比较 API 中的 commit SHA，确认上游可访问。

重试上传先查看已有资产。未完成的 `starter` 或大小不符资产仅在确认属于本次失败上传后删除并重试该资产；已成功的同名资产保持原样，内容变化则选新 tag／名称。不要使用 `--clobber` 掩盖不一致。

## 可复用 Skill 的安装与公开范围

仓库根目录可直接作为 Skill，包含 `SKILL.md`、`agents/openai.yaml`、`scripts/`、`references/`。可在仓库根目录提供给人的 README 和代码 LICENSE。代码／方法许可只覆盖这些原创文本和脚本，不包含引用项目的游戏资产。

```sh
git clone https://github.com/OWNER/SKILL-REPOSITORY.git \
  "$HOME/.codex/skills/sts2-mod-workflow"
```

已有安装先检查其修改，再更新；不覆盖用户自定义内容。发布前执行技能结构检查和脚本 fixture 测试，确认没有本机绝对路径、用户存档、令牌、游戏二进制或资源包进入公开提交。
