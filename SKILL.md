---
name: sts2-mod-workflow
description: 制作、维护和发布《杀戮尖塔2》C#／Godot Mod，覆盖资源接入、原生桥接、验证、带哈希的成品打包、GitHub Releases 与 Steam 创意工坊上传。适用于新建 Mod、角色表现扩展、现有项目升级和发布任务。
---

# 杀戮尖塔2 Mod 制作与发布

将需求做成可构建、可安装、可回退的 STS2 Mod，再按用户指定的渠道和可见性发布。优先复用项目现有工具链、目录、稳定 ID 和验收入口。

## 先确定本轮起点

读取项目 `AGENTS.md`、产品／开发／状态文档，检查 Git 状态、实际 manifest、构建清单和验收报告。用户只要求打包时，优先使用与源码版本相符且已经通过验收的现有产物；有源码变更或输入不一致时才重构建并更新相关验证。

记录目标游戏版本／分支、操作系统／CPU、Mod ID、运行依赖、发布渠道及可见性。沿用用户已给出的授权；未指定 GitHub 仓库时先查同名仓库，素材成品默认私有，公开方法与代码按用户要求。Steam 与 GitHub 是两个独立的上传目标，GitHub 发布不会自动建立工坊条目。

## 按任务读取资料

- 新建、接入角色或修复运行问题：读 [development.md](references/development.md)，覆盖资源、C#／GDScript、玩家状态、性能、画面与存档保全。
- 打包、安装、GitHub 发布：读 [packaging-and-github.md](references/packaging-and-github.md)，使用下面两个脚本及项目原有安装器。
- 创意工坊创建／更新：读 [steam-workshop.md](references/steam-workshop.md)，核实 Mega Crit 官方上传器当前版本，再准备工作区。实际上传沿用用户指定的账号、条目与可见性。
- 当前工作区属于 Reverse1999Roster：另读 [reverse1999-project.md](references/reverse1999-project.md)，其中是项目专用的架构和历史实例，不能套成所有 STS2 Mod 的固定目录或角色数量。

## 必须保留的边界

- manifest、DLL、PCK、原生扩展和许可作为同一产物验证。存在 Cubism 等原生库时逐平台构建；平台名参数只标注产物，脚本不会将 macOS 库转换为 Windows 库。
- 只把构建清单中已经验收的文件加入成品；临时 QA 模组、旧包副本、存档、设置和令牌不进入成品或公开 Skill。
- 测试结论跟随文件哈希。独立引擎、原生桥接、安装读回、真实流程与双机器联机分别记录，按改动范围选择测试和继承未变资源的证据。
- 安装前确认游戏正常退出；使用现有安装／回退脚本，不替换运行中的 Mod。安装器备份的范围按实际记录说明，原生存档另做快照。
- 发布方法、原创脚本的许可与游戏／第三方素材权利分别说明。公开仓库可只包含 Skill；成品用用户指定的私有 Release 保存。
- 外部发布失败后先读回远端状态，再按已有仓库／tag／工坊 ID 继续，避免重复创建或覆盖已有资产。

## 可执行助手

`scripts/package_mod.py`（Python 3.9+，标准库）要求 `build.json` 的 `files` 为相对路径到 SHA-256 的映射，验收 JSON 具有 `passed=true`、相同 `version` 和完整匹配的 `artifacts` 映射。现有项目采用不同格式时先从真实报告生成适配记录；不能填入猜测的通过值。

```sh
python3 /path/to/sts2-mod-workflow/scripts/package_mod.py \
  --project /path/to/project --mod-id ExampleMod --platform macos-arm64 \
  --install-notes /path/to/INSTALL.md \
  --output /path/to/output/ExampleMod-1.0.0-macos-arm64-release.zip
```

脚本保留 Mod 文件夹结构，加入 `RELEASE/INSTALL.md`、清单和校验文档；流式检查所有 ZIP 条目的 SHA-256 与 CRC。`--reuse-zip` 可复用只含相同已验收文件的旧 ZIP，减少大型 PCK 重新压缩。`--verify <ZIP>` 只执行读回校验。

`scripts/prepare_workshop.py` 从发布 ZIP 生成官方 `content/`、`workshop.json`、预览图与本地记录。依赖参数形式为 `游戏manifest中的ID=数字工坊ID`。它只准备本地工作区；不会调用 Steam。默认不覆盖已有工作区，保留已发布条目的 `mod_id.txt`。

```sh
python3 /path/to/sts2-mod-workflow/scripts/test_workflow.py
```

完成时给出成品位置、版本／平台、校验结果、实际 GitHub／工坊链接和已执行的验证层级。发布完成须有远端读回证据；只准备了工作区就写“已准备”。
