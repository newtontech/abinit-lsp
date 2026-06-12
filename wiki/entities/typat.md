# typat

> 类型：输入变量 (Input Variable)
> 创建日期：2026-06-12
> 来源数：3

## 简介

`typat` 是一个整数数组，将每个原子映射到其原子类型索引（1-based indexing）。数组长度必须等于 [[natom]]。

来源：[[completion.py]]

## 关键属性

- **类型**：整数数组
- **长度**：必须等于 `natom`
- **索引范围**：[1, [[ntypat]]]
- **规则代码**：ABINIT103（一致性检查）

## 格式

```
typat type1 type2 type3 ...
```

## 示例

```
# 两个硅原子（相同类型）
natom 2
ntypat 1
typat 1 1

# 4个原子，2种类型
natom 4
ntypat 2
typat 1 1 2 2
```

来源：[[test fixtures/si_scf.abi]]

## 诊断规则

### ABINIT103 - 一致性检查

#### 类型索引超出范围

当 `typat` 值不在 [1, ntypat] 范围内时：

```json
{
  "code": "ABINIT103",
  "severity": "error",
  "message": "typat value 3 is out of range [1, 2] defined by ntypat"
}
```

来源：[[lint.py]]

#### 与 znucl 的交叉检查

即使 `ntypat` 未定义，如果 `znucl` 存在，也会推断类型数量：

```json
{
  "code": "ABINIT103",
  "message": "typat value 3 exceeds the 2 types implied by znucl"
}
```

来源：[[lint.py]]

## 语法快捷方式

可以使用星号表示法重复值：

```
# 等价写法
typat 1 1 1 1 1 1
typat 6*1
```

来源：[[parser.py]]

## 相关实体/概念

- [[natom]] - 原子总数
- [[ntypat]] - 原子类型数量
- [[znucl]] - 核电荷数（定义类型）
- [[xred]] - 原子坐标

## 验证清单

- [ ] `typat` 数组长度等于 `natom`
- [ ] 所有 `typat` 值在 [1, ntypat] 范围内
- [ ] `typat` 值与 [[znucl]] 定义的化学类型一致

## 历史更新

- 2026-06-12: 创建页面
