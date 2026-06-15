# ecut

> 类型：输入变量 (Input Variable)
> 创建日期：2026-06-12
> 来源数：3

## 简介

`ecut` (energy cutoff) 是 ABINIT 中控制平面波基组大小的关键参数，定义了平面波展开的能量截断值（单位：Hartree）。

来源：[[completion.py]]

## 关键属性

- **单位**：Hartree (哈特里)
- **类型**：浮点数
- **典型值范围**：10-50 Hartree（取决于赝势）
- **必需性**：必需变量
- **规则代码**：ABINIT101（缺失警告）

## 物理意义

平面波基组大小由 `ecut` 决定：
- 更大的 `ecut` = 更大的基组 = 更精确的结果
- 更小的 `ecut` = 计算更快但精度降低
- 必须针对每个赝势进行收敛性测试

## 示例

```
ecut 30.0
```

来源：[[test fixtures/rules/valid_complete.abi]]

## 诊断规则

### ABINIT101 - 缺失警告

当 `ecut` 未定义时触发：

```json
{
  "code": "ABINIT101",
  "severity": "warning",
  "message": "ecut is a required variable for ABINIT calculations"
}
```

来源：[[lint.py]]

### ABINIT031 - 值范围检查

`ecut` 必须为正值：

```json
{
  "code": "ABINIT031",
  "message": "ecut should be a positive value (plane-wave energy cutoff)"
}
```

来源：[[analyzer.py]]

## 相关实体/概念

- [[ecutsm]] - 截断能平滑
- [[nband]] - 能带数量
- [[基组收敛性]] - Basis Set Convergence

## 最佳实践

1. 始终进行 `ecut` 收敛性测试
2. 从较低值（如 15 Ha）开始，逐步增加直到能量变化小于预期精度
3. 不同的赝势需要不同的 `ecut` 值
4. 结构优化时可能需要稍高的 `ecut` 值

## 官方参考 / Official Reference

- ABINIT docs: <https://docs.abinit.org/variables/ecut/>
- Tutorial: <https://docs.abinit.org/tutorial/base1/> (ecut convergence testing)
- 参见: [[upstream-sources]] for complete variable index

## 历史更新

- 2026-06-12: 创建页面
- 2026-06-13: 添加官方参考链接和 LSP hover 文档来源

## Traceability Sources

- Raw evidence: `raw/assets/upstream-sources.md`
