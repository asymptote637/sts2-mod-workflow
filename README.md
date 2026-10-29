# STS2 Mod Workflow

《杀戮尖塔2》Mod 制作与发布 Skill：从需求、C#／Godot 桥接、角色资源与演出，到测试、安装／回退、可核对的打包、GitHub Releases 和 Steam 创意工坊上传。

来源实例是 Reverse1999Roster 1.5.2；通用流程与项目约定分开维护。仓库只提供原创方法文档和脚本，游戏素材成品独立保存。

## 安装与调用

```sh
git clone https://github.com/asymptote637/sts2-mod-workflow.git \
  "$HOME/.codex/skills/sts2-mod-workflow"
```

在 Codex 中调用：

```text
使用 $sts2-mod-workflow，将当前项目最新已验收版本打包，
核对平台依赖，准备 GitHub Release 和 Steam 工坊上传材料。
```

Skill 入口：[SKILL.md](SKILL.md)。安装目录已有内容时先检查差异，保留本地自定义修改。

## 内容

| 文件 | 用途 |
| --- | --- |
| [development.md](references/development.md) | 资源、C#／GDScript、演员生命周期、状态／联机、性能和验证 |
| [packaging-and-github.md](references/packaging-and-github.md) | ZIP、安装／回退、仓库、Release 与远端哈希 |
| [steam-workshop.md](references/steam-workshop.md) | 官方跨平台上传器、工作区、依赖、首次上传与更新 |
| [reverse1999-project.md](references/reverse1999-project.md) | 项目专用架构与已验证实例 |
| [package_mod.py](scripts/package_mod.py) | 按已验收 SHA-256 清单打包及读回，Python 3.9+ 标准库 |
| [prepare_workshop.py](scripts/prepare_workshop.py) | 从发布 ZIP 生成官方上传器工作区，不执行上传 |

```sh
python3 scripts/test_workflow.py
```

测试覆盖清单排除、源文件改变、过期／失败验收、路径边界、重复 ZIP、篡改读回、依赖映射及现有工坊条目保留。脚本不更改游戏安装和存档。

## 来源与许可

上传流程依据 [Mega Crit 官方上传器](https://github.com/megacrit/sts2-mod-uploader)，核实日期 2026-10-29，已在 macOS ARM64 本机运行官方 v0.2.0 的帮助及工作区创建命令。再次实际上传前核实当前工具版本。

原创 Skill、文档和脚本采用 [MIT](LICENSE)。许可不覆盖原游戏素材、字体、音频、第三方原生库，也不随仓库分发这些文件。
