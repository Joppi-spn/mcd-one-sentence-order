# 麦当劳 MCP 工具清单（tool_catalog）

- **Server**：`mcd-mcp` → `https://mcp.mcd.cn`（streamable HTTP，Bearer 鉴权）
- **版本**：1.0.0 ｜ **工具总数**：35
- 完整 `tools/list` 原始定义见官方 MCP；下表为本 Skill 实际用到的核心工具及其调用映射。

## 本 Skill 直接调用的工具

| 工具 | 用途 | 对应 Skill 步骤 |
|------|------|----------------|
| `query-meals` | 餐品列表（到店/外送），含商品 code 与价格 | 拉菜单 |
| `query-meal-detail` | 餐品详情：组成、可特调、可换套餐 | 拉菜单 / 微调 |
| `list-nutrition-foods` | 营养成分：能量/蛋白质/脂肪/碳水/钠/钙 | 热量 & 蛋白来源 |
| `calculate-price` | 计算价格（含优惠，返回单位**分**） | 价格校验 |
| `create-order` | 创建订单（到店 orderType=1 / 外送 orderType=2） | 下单 |
| `cancel-order` | 取消订单 | 异常 |
| `query-order` | 查询订单详情/状态 | 异常 |
| `query-nearby-stores` | 到店门店（自取 beType=1 / 得来速 beType=5） | 门店路由 |
| `delivery-query-stores` | 外送可配送门店（beType=2 麦乐送 / 6 团餐） | 门店路由 |
| `delivery-query-addresses` | 查询配送地址列表 | 地址 |
| `delivery-create-address` | 创建配送地址 | 地址 |

## 其余可用工具（场景扩展）

**优惠券 / 营销**：`available-coupons`、`query-store-coupons`、`query-my-coupons`、`auto-bind-coupons`、`query-survey-coupon`、`campaign-calendar`、`query-promotions`
**积分 / 抽奖 / 商城**：`query-my-account`、`query-lottery-info`、`draw-lottery`、`query-my-prizes`、`mall-points-products`、`mall-product-detail`、`mall-create-order`、`mall-order-list`、`mall-order-detail`
**派对 / 活动**：`query-party-city`、`query-party-store`、`query-party-store-date`、`query-party-store-session`、`party-order-create`、`query-meal-assistance`
**通用**：`order-list`、`now-time-info`

## 调用路由要点

- `orderType` + `beType` + `beCode` 组合决定门店路由：
  - 到店自取(1) 不传 beCode
  - 得来速(5) beCode 来自 `query-nearby-stores`
  - 麦乐送(2)/团餐(6) beCode 来自 `delivery-query-stores`
- `calculate-price` / `create-order` 的 items 含特调 `modification`：选中项 key=`selectedKey`，未选中但有 `unselectedKey` 的项也必须传 `unselectedKey`。
- `create-order` 成功后引导用户支付，再回报"支付完成/失败"并查 `query-order`。
- 抽奖/兑换类工具多有权限与时间校验，禁止替用户决定或臆造结果。
