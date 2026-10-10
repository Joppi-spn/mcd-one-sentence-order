# MCP 集成说明（MCP_INTEGRATION）

本文档说明「麦麦一句话点餐」实际使用的**麦当劳 MCP Server、调用的 Tool、调用流程与业务价值**。

## 一、实际使用的 MCP Server

| 项 | 值 |
|----|----|
| Server 名称 | `mcd-mcp` |
| 接入地址 | `https://mcp.mcd.cn` |
| 传输协议 | Streamable HTTP（streamablehttp） |
| 鉴权方式 | Bearer Token（配置于 `~/.workbuddy/mcp.json`，**不入库**） |
| 版本 | 1.0.0 |
| 工具总数 | 35（本 Skill 直接调用约 11 个，其余用于场景扩展） |

> 配置模板见 `config.example.json`；真实 Token 由运行环境注入，参赛仓库仅保留占位符。

## 二、调用的 Tool（按使用频率）

### 核心链路（必须）
| 工具 | 作用 | 在 Skill 中的位置 |
|------|------|------------------|
| `query-meals` | 获取餐品列表（到店/外送），含商品 code 与价格 | 拉菜单 |
| `list-nutrition-foods` | 获取营养成分：能量/蛋白质/脂肪/碳水/钠/钙 | 满足热量上限、蛋白质含量约束 |
| `query-meal-detail` | 餐品详情：组成、可特调、可换套餐 | 拉菜单 / 微调 |
| `calculate-price` | 计算价格（含优惠），返回单位**分** | 价格校验（展示 ÷100） |
| `create-order` | 创建订单（到店 orderType=1 / 外送 orderType=2） | 下单闭环 |
| `cancel-order` | 取消订单 | 异常处理 |
| `query-order` | 查询订单状态 | 异常处理 |
| `query-nearby-stores` | 到店门店（自取 beType=1 / 得来速 beType=5） | 门店路由 |
| `delivery-query-stores` | 外送可配送门店（beType=2 / 6） | 门店路由 |
| `delivery-query-addresses` | 配送地址列表 | 地址解析 |
| `delivery-create-address` | 创建配送地址 | 地址解析 |

### 扩展链路（可选，提升体验）
- 优惠券：`available-coupons`、`query-store-coupons`、`query-my-coupons`、`auto-bind-coupons`
- 营销活动：`campaign-calendar`、`query-promotions`（团餐满减/满折）
- 积分商城：`query-my-account`、`mall-points-products`、`mall-create-order` 等

## 三、调用流程

```
用户一句话
   │
   ▼
[1] parse_slots(text)  → 槽位（热量/预算/品类/口味/忌口/人数/场景）
   │                      （scripts/recommend.py）
   ▼
[2] 选路由：到店(beType=1/5) 或 外送(beType=2/6)
   │  ├─ 到店：query-nearby-stores        → storeCode [+ beCode]
   │  └─ 外送：delivery-query-addresses → delivery-query-stores → storeCode + beCode
   ▼
[3] 拉数据：
   │  ├─ query-meals(storeCode, orderType, beCode)     → 餐品 + 价格 + code
   │  └─ list-nutrition-foods()                        → 热量 / 蛋白质
   │  └─ query-meal-detail(...)（按需）                → 组成 / 特调
   ▼
[4] solve(menu, slots)  → 硬约束过滤 → 组合生成 → 打分排序 → 解释
   │                      （scripts/recommend.py，Top 1–3）
   ▼
[5] calculate-price(items, storeCode, orderType, beCode) → 含优惠总价（分→元）
   ▼
[6] 输出推荐（清单 / 热量 / 价格 / 蛋白质 / 解释）
   │
   ▼
[7] 用户确认 → create-order → 引导支付 → query-order 查状态
   │
   └─ 异常：MCP 超时/报错 → 重试1次 → 回退本地菜单基线并标注"以门店为准"
```

**路由规则**：`orderType` + `beType` + `beCode` 三元组决定门店；到店自取不传 beCode，得来速/麦乐送/团餐需传 beCode（分别来自 `query-nearby-stores` / `delivery-query-stores`）。

## 四、业务价值

1. **降低决策成本**：把"翻菜单半小时"压缩成一句话，特别适合选择困难、通勤间隙点餐。
2. **精准控卡 / 控预算**：用 `list-nutrition-foods` 的真实营养字段做硬约束，健身与预算人群可量化管理摄入。
3. **解释可信**：每个推荐都带价格/热量/蛋白质/排名的量化解释，区别于"盲推列表"，提升采纳率。
4. **闭环可下单**：从咨询到 `create-order` 全链路打通，真正"一句话点完"。
5. **可扩展**：优惠券、团餐满减、积分商城等工具已预留扩展位，可平滑升级为企业团餐助手。
6. **健壮性**：MCP 不可用时优雅降级到本地基线，避免体验中断。

## 五、合规与降级

- 所有价格、热量、蛋白质数字**必须来自 MCP 实时返回**，禁止编造。
- 下单、领券、抽奖等写操作均以获得用户明确确认为前提。
- 鉴权 Token 不进入代码仓库；离线演示数据已显式标注"以门店为准"。
