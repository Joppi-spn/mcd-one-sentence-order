# 麦麦一句话点餐（mcd-one-sentence-order）

> 基于麦当劳 MCP 的 Agent Skill：用户说一句话，智能体推荐符合**热量、预算、口味偏好**的餐品组合，并给出数据支撑的解释。

## 项目介绍

「麦麦一句话点餐」是一个面向 [WorkBuddy](https://www.workbuddy.cn) 的 Agent Skill。它把"帮我点份麦当劳"这类自然语言需求，自动拆成结构化约束（热量上限、预算上限、想吃的品类、口味倾向、忌口、人数、场景），再调用**麦当劳官方 MCP（`mcd-mcp`）**拉取实时菜单与营养数据，在约束内筛选并组合出 1–3 个最优方案，每个方案都带**价格、热量、蛋白质**和一句**为什么推荐**的解释；无解时不报"没有方案"，而是给出可执行的替代路径（如"热量放宽 80 kcal 就能吃上麦辣鸡腿堡"）。

核心理念：**不堆砌列表，而是像营养师 + 精算师一样解释每个推荐**。

## 安装方法

### 前置条件
- 已安装并登录 WorkBuddy。
- 已获得麦当劳 MCP（`mcd-mcp`）的访问凭证（Bearer Token）。

### 步骤
1. 将本目录 `mcd-one-sentence-order/` 放入用户级技能目录：
   - Windows：`%USERPROFILE%\.workbuddy\skills\mcd-one-sentence-order\`
   - macOS / Linux：`~/.workbuddy/skills/mcd-one-sentence-order\`
2. 在 `~/.workbuddy/mcp.json` 中注册 MCP（参考 `config.example.json`，**把占位符替换为你的真实 Token**）：
   ```json
   {
     "mcpServers": {
       "mcd-mcp": {
         "type": "streamablehttp",
         "url": "https://mcp.mcd.cn",
         "headers": { "Authorization": "Bearer <YOUR_MCD_MCP_TOKEN>" }
       }
     }
   }
   ```
3. 在 WorkBuddy 中启用 `mcd-one-sentence-order` 技能，直接对智能体说出需求即可。

### 独立运行推荐引擎（可选）
无需 MCP 也能本地验证算法：
```bash
cd mcd-one-sentence-order/scripts
python recommend.py "预算30元要低卡"
python recommend.py "两个人吃带点辣的"
```

## 使用示例

**输入**：「预算 30 元要低卡」

**输出**：
```
解析槽位：热量上限 = 800 kcal ｜ 预算上限 = ¥30 ｜ 人数 = 1
  ⚠️ 使用默认假设：热量上限 800 kcal

推荐 1：吉士汉堡×1 + 苹果片×1 + 零度可乐×1
  合计热量 360 kcal ｜ 合计价格 ¥29 ｜ 蛋白质 15.5 g
  解释：热量仅 360 kcal，是预算内偏低的组合。
```

**输入**：「两个人吃带点辣的」

**输出**：
```
解析槽位：热量上限 = 800 kcal ｜ 预算上限 = ¥40 ｜ 人数 = 2
  ⚠️ 使用默认假设：热量上限 800 kcal, 预算上限 ¥40

推荐 1：麦辣鸡腿堡×1 + 麦辣鸡翅(2块)×1 + 零度可乐×1
  合计热量 760 kcal ｜ 合计价格 ¥43.5 ｜ 蛋白质 42 g
  解释：满足你对「辣」的偏好；蛋白质 42g，在候选中排名前 10%。
```

## 目标用户

- **控卡 / 健身人群**：用"低卡""健身后补蛋白"等约束精准搭配。
- **预算敏感用户**：学生、打工人用预算上限找性价比组合。
- **选择困难症**：一句话搞定"吃什么"，不翻菜单。
- **外送 / 团餐用户**：结合门店、地址、优惠券与满减规则下单。
- **开发者 / 参赛者**：作为"自然语言 → MCP 工具编排"的参考实现。

## 文件结构

```
mcd-one-sentence-order/
├── SKILL.md                 # 技能核心：触发词、槽位逻辑、MCP 调用流程、输出格式
├── README.md                # 项目介绍、安装、示例、目标用户
├── CONTEST_DECLARATION.md   # 参赛声明
├── MCP_INTEGRATION.md       # MCP Server / Tool / 调用流程 / 业务价值
├── workbuddy.md             # WorkBuddy 开发对话记录
├── scripts/
│   └── recommend.py         # 槽位提取 + 约束求解（可独立运行）
├── references/
│   └── tool_catalog.md      # 麦当劳 MCP 工具清单与调用映射
└── config.example.json      # 配置模板（不含真实 Token）
```
