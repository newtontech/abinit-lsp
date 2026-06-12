# ntypat

> 类型：输入变量 (Input Variable)
> 创建日期：2026-06-12
> 来源数：2

## 简介

`ntypat` 定义晶胞中不同原子类型的数量（化学元素种类数）。

来源：[[completion.py]]

## 关键属性

- **类型**：正整数
- **典型值**：1-10（大多数材料）
- **最小值**：1

## 用途

`ntypat` 决定以下数组的维度：
- [[znucl]] 数组长度为 `ntypat`
- [[amu]] 数组长度为 `ntypat`
- [[typat]] 中的类型索引范围为 [1, ntypat]

## 示例

```
# 单质硅（1种原子类型）
ntypat 1
znucl 14
typat 1 1

# 化合物（2种原子类型）
ntypat 2
znucl 14 8
typat 1 1 2 2
```

## 与其他变量的关系

### 与 znucl 的关系

[[znucl]] 数组长度必须等于 `ntypat`：

```
ntypat 2
znucl 14 8  # 正确：2个值
```

错误情况（ABINIT103）：

```
ntypat 2
znucl 14    # 错误：只有1个值
```

来源：[[lint.py]]

### 与 typat 的关系

`typat` 中的类型索引必须在 [1, ntypat] 范围内：

```
ntypat 2
typat 1 2 1 2  # 正确
typat 1 3 1 2  # 错误：3超出范围
```

## 诊断规则

### ABINIT031 - 最小值检查

`ntypat` 必须至少为 1：

```json
{
  "code": "ABINIT031",
  "message": "keyword 'ntypat' value 0 is below minimum 1"
}
```

来源：[[analyzer.py]]

## 相关实体/概念

- [[typat]] - 原子类型数组
- [[znucl]] - 核电荷数数组
- [[natom]] - 原子总数

## 常见错误

1. `znucl` 长度不等于 `ntypat`
2. `typat` 中包含超出 [1, ntypat] 的索引
3. `ntypat` 设置为 0

## 官方参考 / Official Reference

- ABINIT docs: <https://docs.abinit.org/variables/ntypat/>
- 参见: [[upstream-sources]] for complete variable index

## 历史更新

- 2026-06-12: 创建页面
- 2026-06-13: 添加官方参考链接
