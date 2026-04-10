# ============================================
# tools/knowledge_l1.py - 知识库检索业务层
# 职责: 文档索引管理 + 语义搜索
#
# 存储结构:
#   data/knowledge/{collection}/
#     ├── *.txt / *.md / *.pdf     原始文档
#     └── _index.json               向量缓存
#
# 嵌入渠道: 从 config/llm.json channels 中读取 embedding_* 渠道
# ============================================

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 项目根
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_KNOWLEDGE_DIR = _PROJECT_ROOT / "data" / "knowledge"


def _tool_search_knowledge(input_obj: dict, npc, context) -> str:
    """
    搜索知识库

    Args:
        input_obj: {"query": "...", "collection": "...", "top_k": 5}
    """
    query = input_obj.get("query", "").strip()
    collection = input_obj.get("collection", "")
    top_k = input_obj.get("top_k", 5)

    if not query:
        return "错误: 缺少 query 参数"

    # 确定搜索范围
    if collection:
        collections = [collection]
    else:
        # 搜索所有集合
        if not _KNOWLEDGE_DIR.exists():
            return "知识库为空 (data/knowledge/ 目录不存在)"
        collections = [d.name for d in _KNOWLEDGE_DIR.iterdir() if d.is_dir() and not d.name.startswith("_")]

    if not collections:
        return "知识库为空 (没有任何集合)"

    # 获取 query 向量
    query_vec = _get_embedding(query)
    if query_vec is None:
        # 回退到关键词搜索
        return _keyword_search(query, collections, top_k)

    # 语义搜索
    results = []
    for coll_name in collections:
        coll_dir = _KNOWLEDGE_DIR / coll_name
        if not coll_dir.exists():
            continue

        # 加载或构建索引
        index = _load_or_build_index(coll_dir)
        if not index:
            continue

        # 计算相似度
        for chunk in index:
            vec = chunk.get("vector")
            if not vec:
                continue
            score = _cosine_similarity(query_vec, vec)
            results.append({
                "collection": coll_name,
                "file": chunk.get("file", ""),
                "text": chunk.get("text", ""),
                "score": score,
            })

    if not results:
        return f"在知识库中未找到与 '{query}' 相关的内容"

    # 排序取 top_k
    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:top_k]

    # 格式化输出
    output = f"找到 {len(results)} 条相关结果:\n\n"
    for i, r in enumerate(results, 1):
        score_pct = f"{r['score'] * 100:.1f}%"
        output += f"[{i}] [{r['collection']}] {r['file']} (相关度: {score_pct})\n"
        # 截断过长文本
        text = r["text"]
        if len(text) > 500:
            text = text[:500] + "..."
        output += f"{text}\n\n"

    return output.strip()


# ========== 嵌入 API ==========

def _get_embedding_config() -> Optional[Dict]:
    """从 config/llm.json 获取 embedding 渠道配置"""
    config_path = _PROJECT_ROOT / "config" / "llm.json"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        channels = config.get("channels", {})
        # 找 embedding_ 开头的渠道
        for name, cfg in channels.items():
            if name.startswith("embedding"):
                return cfg
        return None
    except Exception:
        return None


def _get_embedding(text: str) -> Optional[List[float]]:
    """调用云端 embedding API 获取向量"""
    import urllib.request
    import urllib.error

    config = _get_embedding_config()
    if not config:
        print("[Knowledge] 未配置 embedding 渠道，回退到关键词搜索")
        return None

    provider = config.get("provider", "openai")
    base_url = config.get("base_url", "").rstrip("/")
    api_key = config.get("api_key", "")
    models = config.get("models", {})
    model = models.get("default", "embedding-3")

    # 构建请求
    if provider == "zhipu" or provider == "openai":
        url = f"{base_url}/v1/embeddings"
        body = json.dumps({"model": model, "input": text}).encode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
    else:
        print(f"[Knowledge] 不支持的 embedding provider: {provider}")
        return None

    try:
        req = urllib.request.Request(url, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())

        # OpenAI 兼容格式
        data = result.get("data", [])
        if data and "embedding" in data[0]:
            return data[0]["embedding"]

        print(f"[Knowledge] embedding 响应格式异常: {list(result.keys())}")
        return None

    except Exception as e:
        print(f"[Knowledge] embedding API 调用失败: {e}")
        return None


# ========== 索引管理 ==========

def _load_or_build_index(coll_dir: Path) -> List[Dict]:
    """加载索引缓存，若不存在或过期则重建"""
    index_path = coll_dir / "_index.json"

    # 收集文档文件
    doc_files = []
    for ext in ["*.txt", "*.md"]:
        doc_files.extend(coll_dir.glob(ext))

    if not doc_files:
        return []

    # 计算文档指纹 (用于判断是否需要重建)
    fingerprint = _calc_fingerprint(doc_files)

    # 尝试加载缓存
    if index_path.exists():
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            if cached.get("fingerprint") == fingerprint:
                return cached.get("chunks", [])
        except Exception:
            pass

    # 重建索引
    print(f"[Knowledge] 构建索引: {coll_dir.name} ({len(doc_files)} 个文档)")
    chunks = []
    for doc_file in doc_files:
        file_chunks = _split_document(doc_file)
        for text in file_chunks:
            vec = _get_embedding(text)
            chunks.append({
                "file": doc_file.name,
                "text": text,
                "vector": vec,  # 可能为 None (无 embedding 配置时)
            })

    # 保存缓存
    cache_data = {"fingerprint": fingerprint, "chunks": chunks}
    try:
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False)
    except Exception as e:
        print(f"[Knowledge] 保存索引失败: {e}")

    return chunks


def _split_document(filepath: Path, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """将文档切分为片段"""
    try:
        text = filepath.read_text("utf-8")
    except Exception:
        return []

    if not text.strip():
        return []

    # 按段落优先切分
    paragraphs = text.split("\n\n")
    chunks = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current) + len(para) <= chunk_size:
            current += ("\n\n" + para) if current else para
        else:
            if current:
                chunks.append(current)
            # 长段落按字数切
            if len(para) > chunk_size:
                for i in range(0, len(para), chunk_size - overlap):
                    chunks.append(para[i:i + chunk_size])
            else:
                current = para
                continue
            current = ""

    if current:
        chunks.append(current)

    return chunks if chunks else [text[:chunk_size]]


def _calc_fingerprint(files: List[Path]) -> str:
    """计算文件列表指纹"""
    h = hashlib.md5()
    for f in sorted(files, key=lambda x: x.name):
        h.update(f.name.encode())
        h.update(str(f.stat().st_mtime).encode())
        h.update(str(f.stat().st_size).encode())
    return h.hexdigest()


# ========== 向量计算 (L2 原子逻辑) ==========

def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """余弦相似度"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ========== 关键词回退 ==========

def _keyword_search(query: str, collections: List[str], top_k: int) -> str:
    """无 embedding 时的关键词搜索"""
    keywords = query.lower().split()
    results = []

    for coll_name in collections:
        coll_dir = _KNOWLEDGE_DIR / coll_name
        if not coll_dir.exists():
            continue

        for ext in ["*.txt", "*.md"]:
            for doc_file in coll_dir.glob(ext):
                try:
                    text = doc_file.read_text("utf-8")
                except Exception:
                    continue

                # 按段落搜索
                paragraphs = text.split("\n\n")
                for para in paragraphs:
                    para_lower = para.lower()
                    score = sum(1 for kw in keywords if kw in para_lower)
                    if score > 0:
                        results.append({
                            "collection": coll_name,
                            "file": doc_file.name,
                            "text": para.strip(),
                            "score": score / len(keywords),
                        })

    if not results:
        return f"在知识库中未找到与 '{query}' 相关的内容"

    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:top_k]

    output = f"找到 {len(results)} 条相关结果 (关键词匹配):\n\n"
    for i, r in enumerate(results, 1):
        text = r["text"][:500] + "..." if len(r["text"]) > 500 else r["text"]
        output += f"[{i}] [{r['collection']}] {r['file']}\n{text}\n\n"

    return output.strip()
