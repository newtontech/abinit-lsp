# natom

> 类型：输入变量 (Input Variable)
> 创建日期：2026-06-12
> 来源数：3

## 简介

`natom` 定义晶胞中原子的数量，是 ABINIT 结构定义的必需参数。

来源：[[completion.py]]

## 关键属性

- **类型**：正整数
- **必需性**：必需（结构计算）
- **规则代码**：ABINIT102（缺失错误）
- **约束**：natom ≥ 1

## 用途

`natom` 决定了多个数组的维度：
- [[typat]] 数组长度为 `natom`
- [[xred]] / [[xcart]] 数组为 `natom × 3`
- 影响内存分配和计算规模

## 示例

```
natom 2
typat 1 1
xred 0.0 0.0 0.0
     0.25 0.25 0.25
```

来源：[[test fixtures/si_scf.abi]]

## 诊断规则

### ABINIT102 - 缺失错误

当 `natom` 未定义时触发：

```json
{
  "code": "ABINIT102",
  "severity": "error",
  "message": "natom is required to define the crystal structure"
}
```

来源：[[lint.py]]

### ABINIT031 - 正值检查

`natom` 必须为正整数：

```json
{
  "code": "ABINIT031",
  "message": "natom must be a positive integer (number of atoms)"
}
```

来源：[[analyzer.py]]

### ABINIT010 - 结构完整性检查

当缺少结构相关变量时触发警告：

```json
{
  "code": "ABINIT010",
  "message": "ABINIT input does not expose enough structure variables for static review"
}
```

来源：[[analyzer.py]]

## 相关实体/概念

- [[ntypat]] - 原子类型数量
- [[typat]] - 原子类型映射
- [[znucl]] - 核电荷数
- [[xred]] - 约化坐标
- [[xcart]] - 笛卡尔坐标

## 验证规则

1. `natom` 必须与 `typat` 数组长度一致
2. `natom` 必须与坐标数组行数一致
3. 对于给定的 `ntypat`，`typat` 中的类型索引必须在 [1, ntypat] 范围内

## 历史更新

- 2026-06-12: 创建页面
