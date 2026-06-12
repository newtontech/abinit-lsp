# ABINIT

> 类型：软件 (Software)
> 创建日期：2026-06-12
> 来源数：4

## 简介

ABINIT 是一个用于材料科学计算的第一性原理软件包，基于密度泛函理论 (DFT) 和许多相关方法。该软件包能够计算总能量、电荷密度、电子结构，以及许多派生性质，包括结构优化、分子动力学、响应函数（声子、介电函数、有效电荷）等。

来源：[[raw/assets/README.md]]

## 关键属性

- **开发语言**：Fortran (主要) + Python
- **许可证**：GPL
- **用途**：材料科学、量子化学计算
- **输入格式**：基于文本的关键词-值对格式
- **典型文件扩展名**：`.abi`, `.abinit`, `.in`

## 输入文件格式

ABINIT 输入文件由关键词-值对组成：

```
keyword value1 value2 ...
keyword = value
```

注释以 `#`、`!` 或 `;` 开头。

来源：[[parser.py]]

## 多数据集计算

ABINIT 支持多数据集计算，通过关键词后缀实现：

```
ecut1 20.0
ecut2 30.0
ndtset 2
```

来源：[[lint.py]]

## LSP 支持

abinit-lsp 项目为 ABINIT 输入文件提供 Language Server Protocol 支持，包括：
- 语法检查
- 关键词补全
- 格式化
- 诊断输出

来源：[[raw/assets/README.md]]

## 相关实体/概念

- [[ecut]] - 平面波截断能
- [[natom]] - 原子数量
- [[typat]] - 原子类型
- [[znucl]] - 核电荷数
- [[SCF]] - 自洽场循环

## 官方参考 / Official References

- ABINIT Homepage: <https://www.abinit.org/>
- Input Variables: <https://docs.abinit.org/variables/>
- Tutorials: <https://docs.abinit.org/tutorial/>
- 参见: [[upstream-sources]] for complete variable index
- 参见: [[diagnostic-engine-v1]] for LSP diagnostic codes
- 参见: [[openqc-agent-context]] for agent integration

## 历史更新

- 2026-06-12: 创建页面，基于 abinit-lsp 项目文档
- 2026-06-13: 添加官方参考链接和交叉引用
