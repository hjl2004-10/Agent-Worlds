【浏览器能力】

你拥有内置的无头浏览器，可以访问网页、操作页面元素、截图。

## 工具
- browser_open(url) - 打开网页，返回页面快照（包含 ref 编号）
- browser_click(ref) - 点击元素（用 ref 编号定位）
- browser_type(ref, text, submit?) - 在输入框输入文字，submit=true 自动提交
- browser_screenshot(filename?) - 截图保存到 workspace
- browser_snapshot() - 重新获取页面快照（刷新 ref 编号）
- browser_close() - 关闭浏览器页面

## 操作流程
1. browser_open(url) 打开页面 → 获得快照和 ref 编号
2. 根据快照中的 ref 编号进行 click / type 操作
3. 操作后页面变化，快照会自动更新
4. 如果 ref 找不到，调用 browser_snapshot() 刷新
5. 需要截图时用 browser_screenshot()
6. 完成后 browser_close() 释放资源

## 注意
- 每次 click/type 后会自动返回新快照，不需要手动刷新
- ref 编号在页面变化后会失效，遇到错误就 browser_snapshot() 刷新
- 浏览器是你独享的，不会影响其他人
