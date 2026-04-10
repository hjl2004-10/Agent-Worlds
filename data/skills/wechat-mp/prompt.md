【微信服务号运营能力】

你可以通过脚本管理微信服务号，包括图文发布、粉丝管理、数据分析等。

## 配置文件

操作前先确认 `workspace/wechat_config.json` 存在，内容格式：
```json
{
  "app_id": "你的AppID",
  "app_secret": "你的AppSecret"
}
```

## 可用操作

所有操作通过 `run_command` 执行 Python 脚本（脚本在 `workspace/scripts/wechat/` 目录下）：

### 1. 素材管理
```
# 上传图片素材 (永久)
run_command: python scripts/wechat/media.py upload_image <图片路径>

# 上传图文素材
run_command: python scripts/wechat/media.py upload_article --title "标题" --content "HTML内容" --thumb_media_id <封面图ID>

# 查看素材列表
run_command: python scripts/wechat/media.py list --type image --count 10
```

### 2. 群发推送
```
# 群发图文消息 (发给所有粉丝)
run_command: python scripts/wechat/publish.py send_article <media_id>

# 预览 (发给指定 openid，测试用)
run_command: python scripts/wechat/publish.py preview <media_id> --openid <openid>
```

### 3. 粉丝管理
```
# 获取粉丝列表
run_command: python scripts/wechat/user.py list --count 100

# 获取粉丝详情
run_command: python scripts/wechat/user.py info <openid>

# 给粉丝打标签
run_command: python scripts/wechat/user.py tag <openid> <tag_name>
```

### 4. 数据统计
```
# 获取粉丝增长数据 (最近7天)
run_command: python scripts/wechat/stats.py user_summary --days 7

# 获取图文阅读数据
run_command: python scripts/wechat/stats.py article_summary --days 7

# 获取消息统计
run_command: python scripts/wechat/stats.py msg_summary --days 7
```

### 5. 自定义菜单
```
# 查看当前菜单
run_command: python scripts/wechat/menu.py get

# 设置菜单 (从JSON文件)
run_command: python scripts/wechat/menu.py set --file scripts/wechat/menu_config.json
```

## 工作流程

1. 写文章：用 write_file 写好 HTML 内容
2. 上传封面图：media.py upload_image
3. 上传图文：media.py upload_article
4. 预览确认：publish.py preview
5. 群发：publish.py send_article

## 注意事项

- 服务号每月只能群发 4 次，谨慎操作
- 群发前务必先用 preview 预览确认
- 图片素材大小限制 10MB
- HTML 内容需要符合微信格式要求（不支持外链图片）
