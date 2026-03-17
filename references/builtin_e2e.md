# 内置E2E测试流程（降级版）

> 当ecc-workflow不可用时的简化E2E实现

## 适用场景

- ecc-workflow未安装
- 用户选择不使用ECC
- 快速验证场景

## E2E测试核心

端到端测试验证整个应用流程。

## 测试步骤

### 1. 识别关键路径

```
用户登录 → 浏览商品 → 加入购物车 → 结账 → 订单确认
```

### 2. 编写测试用例

```python
# 示例：用户登录E2E测试
def test_user_login_flow():
    # 1. 打开登录页
    driver.get("https://example.com/login")

    # 2. 输入凭证
    driver.find_element(By.ID, "username").send_keys("testuser")
    driver.find_element(By.ID, "password").send_keys("password123")

    # 3. 点击登录
    driver.find_element(By.ID, "submit").click()

    # 4. 验证跳转
    assert "/dashboard" in driver.current_url
```

### 3. 运行测试

```bash
# 运行所有E2E测试
pytest e2e/ -v

# 运行单个测试
pytest e2e/test_login.py -v
```

## 测试框架选择

| 框架 | 语言 | 适用场景 |
|------|------|---------|
| Playwright | 多语言 | 现代Web应用 |
| Cypress | JavaScript | 前端E2E |
| Selenium | 多语言 | 传统Web |
| Puppeteer | JavaScript | Chrome自动化 |

## 测试检查清单

- [ ] 关键路径覆盖？
- [ ] 异步操作有等待？
- [ ] 错误场景有测试？
- [ ] 测试独立可运行？
- [ ] 测试数据已准备？

## 常见模式

### 页面对象模式
```python
class LoginPage:
    def __init__(self, driver):
        self.driver = driver

    def login(self, username, password):
        self.driver.find_element(By.ID, "username").send_keys(username)
        self.driver.find_element(By.ID, "password").send_keys(password)
        self.driver.find_element(By.ID, "submit").click()
```

### 行为驱动测试
```python
Scenario: User login
  Given the login page
  When I enter valid credentials
  Then I should be redirected to dashboard
```
