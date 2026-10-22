# EcoGen-Repro

**检查当前结果是否仍对应当前输入文件、样本和参数。**

[English](README.md) · [安装包](https://github.com/yzzzzz7/EcoGen-Repro/releases) · [验证记录](docs/VALIDATION.md)

当前为 **0.2.0 alpha**。它用于科研流程的文件来源核验，运行时仅依赖 Python 标准库，不需要 API 密钥或网络连接。公开示例全部为合成数据；真实用户采用、大文件性能和生物学有效性尚未验证。

## 具体能解决什么问题

假设你已经根据一个最终 VCF 得到了分析结果。后来，VCF、样本名单、参数或分析脚本发生变化，旧结果就需要重新确认来源。

EcoGen-Repro 用文件 SHA256 和配置记录识别这种变化。运行指定分析命令前后，它检查已声明输入是否一致；命令成功后，它记录新输出的来源凭证。之后还可以重新核验输入和结果，导出便于阅读的 HTML 报告。

实际分析仍由你指定的 R、Python 或其他软件完成。工具不计算遗传多样性、有效种群大小、DFE 或灭绝概率，也不替代这些分析的科学诊断。

## 安装

需要 Python 3.10 或更新版本。下载仓库后，在仓库目录运行：

```sh
python -m pip install .
ecogen-repro --version
```

也可以从 [Releases](https://github.com/yzzzzz7/EcoGen-Repro/releases) 下载 `.whl` 安装包，再运行 `python -m pip install 完整安装包路径`。本项目尚未发布到 PyPI。

## 一条命令体验

```sh
ecogen-repro demo --out my-demo
```

`my-demo` 必须是新目录或空目录，其上一级目录需要已经存在。该命令只在指定目录中生成合成示例，依次检查：

| 情形 | 应有结果 |
| --- | --- |
| 原始示例正常运行 | 通过 |
| VCF 内容改变 | 拒绝沿用原记录 |
| 样本顺序改变 | 拒绝沿用原记录 |
| 参数改变 | 拒绝沿用原记录 |
| 输出文件改变 | 原凭证核验失败 |
| 示例文件恢复原样 | 再次通过 |

结束后打开 `my-demo/report.html` 查看输入、样本范围、参数、命令和输出哈希。`demo-results.json` 记录这六项演示的实际结果。故意改变文件后被拒绝，表示软件检查生效。

正常完成后，合成输入和输出会恢复，原始凭证仍可核验。若中途失败，工作文件会保留，方便检查；工具不会自动清空已有目录。

## 接入自己的分析

从 [examples/config.json](examples/config.json) 开始，填写实际项目标识、方法名称和版本、参数、输入路径。输入路径相对于配置文件所在目录；也支持明确的绝对路径。

每个输入都有唯一 `id`、`path` 和可选 `format`：

- `file`：核对完整文件内容，可用于参考基因组、BED、表格、代码和环境锁定文件。
- `vcf`：核对完整文件，同时读取 VCF 表头中的样本 ID 和顺序；支持 `.vcf`、`.vcf.gz`、`.vcf.bgz`。
- `samples`：每行一个样本 ID，拒绝空行、空白字符和重复 ID。

`sample_scope.mode=exact` 要求名单与 VCF 表头完全一致，包括顺序；`subset` 允许明确说明理由的子集，并检查所有选定样本都存在于该 VCF。不同分析使用不同样本范围时，应分别建立配置。

以下示例从仓库目录运行：

```sh
python -m ecogen_repro lock examples/config.json --out examples/lock.json
python -m ecogen_repro check examples/lock.json
python -m ecogen_repro run examples/lock.json --output summary.json --receipt examples/receipt.json -- python summarize.py
python -m ecogen_repro verify examples/receipt.json
python -m ecogen_repro report examples/receipt.json --out examples/report.html
```

`--` 后面的内容是实际执行的命令，运行目录是配置文件所在目录；请替换为你自己的分析命令。`--output` 相对于配置目录，可重复声明多个新输出；`--out` 和 `--receipt` 相对于调用命令时的目录。输出的上级目录必须已经存在。已有锁、凭证、报告和输出不会被覆盖。

输入变化后，应先确认采用的数据、样本和参数，再创建新的锁和结果凭证。仅修改文件名、建立一个新锁，不能证明旧结果来自新输入。

## 报告能说明什么

`report` 会先核验当前输入、凭证和输出，通过后才生成报告。过期结果不能生成新的通过报告。导出的 HTML 是指定时间的静态记录；之后文件改变，HTML 本身不会自动更新。共享后仍应运行 `verify` 重新检查。

通过说明所声明文件在检查时保持来源一致，不代表分析方法和生物学解释已经获得验证。软件版本是使用者声明，需要另行保存实际版本、模型对象和诊断日志。VCF 适配器检查表头样本，不检查全部变异记录、过滤规则、BED 坐标或 SFS 投影。对大文件进行完整哈希会产生磁盘读取开销。

报告和记录可能包含样本 ID、路径、命令和参数，共享前需要检查。工具不上传这些内容。更完整的并发修改、环境依赖和签名限制见 [英文说明](README.md#scope-and-interpretation)。

## 反馈与维护

遇到错误，可以提交 [Issue](https://github.com/yzzzzz7/EcoGen-Repro/issues)，附最小合成示例、运行命令、Python 版本以及预期/实际结果。请保留敏感样本信息和密钥在本地。贡献流程见 [CONTRIBUTING.md](CONTRIBUTING.md)，后续计划见 [ROADMAP.md](ROADMAP.md)。

MIT 许可证。所有示例为新建合成数据，未重新分发独立熊猫论文仓库的数据或脚本。
