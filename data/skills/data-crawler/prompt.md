【网页数据采集能力】

你可以用内置浏览器访问网站，提取公开数据并保存为结构化文件。

## 可用工具

| 工具组 | 用途 |
|--------|------|
| @browser | 打开网页、点击、输入、截图、获取页面快照 |
| @file | 读写文件，保存采集结果 |
| run_command | 执行脚本（如用 Python 处理数据） |

## 采集流程

### 1. 搜索采集（最常用）
用户给出关键词和目标平台，你去搜索并提取结果。

```
步骤:
1. browser_open(平台搜索URL + 关键词)
2. browser_snapshot() 获取搜索结果列表
3. 从快照中提取标题、链接、作者、数据等信息
4. 如需翻页：找到"下一页"按钮的 ref，browser_click(ref)
5. 将结果整理后 write_file 保存为 JSON/CSV
```

### 2. 指定页面采集
用户给出具体 URL，你去提取页面数据。

```
步骤:
1. browser_open(目标URL)
2. browser_snapshot() 获取页面内容
3. 提取需要的数据（正文、评论、数据指标等）
4. write_file 保存结果
```

### 3. 批量采集
用户给出多个 URL 或需要遍历列表页。

```
步骤:
1. 先采集列表页，提取所有详情页链接
2. 逐个 browser_open 每个详情页
3. 提取数据后 browser_close 释放资源
4. 汇总所有结果 write_file 保存
```

## 常用平台搜索 URL

| 平台 | 搜索 URL 格式 |
|------|---------------|
| 百度 | https://www.baidu.com/s?wd=关键词 |
| 知乎 | https://www.zhihu.com/search?type=content&q=关键词 |
| B站 | https://search.bilibili.com/all?keyword=关键词 |
| 微博 | https://s.weibo.com/weibo?q=关键词 |
| 抖音 | https://www.douyin.com/search/关键词 |
| 快手 | https://www.kuaishou.com/search/video?searchKey=关键词 |
| 小红书 | https://www.xiaohongshu.com/search_result?keyword=关键词 |

## 数据保存规范

- 保存路径: `workspace/crawl_data/` 目录下
- 文件名: `{平台}_{关键词}_{日期}.json` 或 `.csv`
- JSON 格式示例:
```json
{
  "query": "关键词",
  "platform": "kuaishou",
  "crawl_time": "2025-01-24 12:00",
  "count": 10,
  "items": [
    {
      "title": "标题",
      "author": "作者名",
      "url": "原文链接",
      "likes": 100,
      "comments": 20,
      "summary": "内容摘要"
    }
  ]
}
```

## 操作要点

1. **先快照再提取**: 每次打开页面或操作后，先看快照了解页面结构
2. **翻页控制**: 一般采集 2-3 页就够，除非用户要求更多
3. **遇到登录墙**: 如果页面要求登录才能查看，告知用户，不要尝试登录
4. **遇到反爬**: 如果页面返回验证码或空白，告知用户，换个方式或稍后重试
5. **完成后关闭**: 采集完毕一定要 browser_close() 释放资源
6. **数据汇报**: 采集完成后，简要汇报采集了多少条数据、保存在哪里
