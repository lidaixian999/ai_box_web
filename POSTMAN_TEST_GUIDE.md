# Postman 文档分析功能测试指南

## 基础配置

### 服务器地址
- **Base URL**: `http://localhost:8000`
- **API Prefix**: `/api/document`

### 完整端点列表
1. `GET /api/document/status` - 获取索引状态
2. `POST /api/document/query` - 文档查询（问答或代码生成）
3. `POST /api/document/query/stream` - 流式查询文档
4. `POST /api/document/rebuild-index` - 重新构建索引

---

## 测试流程

### 步骤 1: 检查索引状态

**请求信息：**
- **Method**: `GET`
- **URL**: `http://localhost:8000/api/document/status`
- **Headers**: 无特殊要求

**请求示例：**
```
GET http://localhost:8000/api/document/status
```

**预期响应：**
```json
{
  "index_loaded": true,
  "index_dir": "C:\\Users\\97049\\Documents\\...\\ws63\\faiss_index",
  "docs_root": "C:\\Users\\97049\\Documents\\...\\ws63",
  "knowledge_dirs": [
    "C:\\Users\\97049\\Documents\\...\\ws63\\demos",
    "C:\\Users\\97049\\Documents\\...\\ws63\\drivers"
  ],
  "embed_model": "nomic-embed-text",
  "gen_model": "qwen3:8b"
}
```

**测试要点：**
- 确认索引是否已加载（`index_loaded: true/false`）
- 确认文档路径配置正确
- 确认使用的模型配置

---

### 步骤 2: 重新构建索引（可选）

**说明**：如果索引未加载或需要更新，可以重新构建索引。注意：首次运行时会自动构建。

**请求信息：**
- **Method**: `POST`
- **URL**: `http://localhost:8000/api/document/rebuild-index`
- **Headers**: 无特殊要求
- **Body**: 无需请求体

**请求示例：**
```
POST http://localhost:8000/api/document/rebuild-index
```

**预期响应：**
```json
{
  "message": "索引重建成功",
  "chunks_count": 150
}
```

**测试要点：**
- 确认索引重建成功
- 记录文档块数量（`chunks_count`）
- 注意：重建索引可能需要一些时间，取决于文档数量

---

### 步骤 3: 测试问答模式查询

**请求信息：**
- **Method**: `POST`
- **URL**: `http://localhost:8000/api/document/query`
- **Headers**: 
  ```
  Content-Type: application/json
  ```
- **Body** (JSON):
```json
{
  "query": "如何使用GPIO驱动LED？",
  "mode": "qa",
  "k": 3
}
```

**请求示例：**
```
POST http://localhost:8000/api/document/query
Content-Type: application/json

{
  "query": "如何使用GPIO驱动LED？",
  "mode": "qa",
  "k": 3
}
```

**预期响应：**
```json
{
  "answer": "根据文档内容，使用GPIO驱动LED的步骤如下：\n1. 初始化GPIO...\n2. 设置引脚模式...",
  "mode": "qa",
  "retrieved_docs_count": 3
}
```

**测试要点：**
- 确认返回了相关答案
- 确认模式为 `qa`
- 确认检索到的文档数量

---

### 步骤 4: 测试代码生成模式

**请求信息：**
- **Method**: `POST`
- **URL**: `http://localhost:8000/api/document/query`
- **Headers**: 
  ```
  Content-Type: application/json
  ```
- **Body** (JSON):
```json
{
  "query": "生成一个LED闪烁的示例代码",
  "mode": "code",
  "k": 4
}
```

**请求示例：**
```
POST http://localhost:8000/api/document/query
Content-Type: application/json

{
  "query": "生成一个LED闪烁的示例代码",
  "mode": "code",
  "k": 4
}
```

**预期响应：**
```json
{
  "answer": "#include <gpio.h>\n\nint main() {\n    // LED闪烁代码...\n}",
  "mode": "code",
  "retrieved_docs_count": 4
}
```

**测试要点：**
- 确认返回了代码内容
- 确认模式为 `code`
- 确认代码格式正确

---

### 步骤 5: 测试自动模式检测

**说明**：当 `mode` 设置为 `"auto"` 时，系统会根据查询内容自动判断是问答还是代码生成。

**测试 5.1: 自动检测为问答模式**

**请求信息：**
- **Method**: `POST`
- **URL**: `http://localhost:8000/api/document/query`
- **Body** (JSON):
```json
{
  "query": "UART接口的参数有哪些？",
  "mode": "auto",
  "k": 3
}
```

**预期响应：**
```json
{
  "answer": "UART接口的主要参数包括：波特率、数据位...",
  "mode": "qa",
  "retrieved_docs_count": 3
}
```

**测试 5.2: 自动检测为代码生成模式**

**请求信息：**
- **Method**: `POST`
- **URL**: `http://localhost:8000/api/document/query`
- **Body** (JSON):
```json
{
  "query": "写一个按钮中断处理的示例",
  "mode": "auto",
  "k": 4
}
```

**预期响应：**
```json
{
  "answer": "#include <gpio.h>\n\n// 按钮中断处理代码...",
  "mode": "code",
  "retrieved_docs_count": 4
}
```

**测试要点：**
- 确认自动模式检测正确
- 问答类型查询应返回 `mode: "qa"`
- 包含"生成"、"写"、"示例"等关键词的查询应返回 `mode: "code"`

---

### 步骤 6: 测试流式查询

**说明**：流式查询支持实时输出，适合生成较长内容。

**请求信息：**
- **Method**: `POST`
- **URL**: `http://localhost:8000/api/document/query/stream`
- **Headers**: 
  ```
  Content-Type: application/json
  ```
- **Body** (JSON):
```json
{
  "query": "生成一个完整的UART通信示例",
  "mode": "code",
  "k": 4
}
```

**请求示例：**
```
POST http://localhost:8000/api/document/query/stream
Content-Type: application/json

{
  "query": "生成一个完整的UART通信示例",
  "mode": "code",
  "k": 4
}
```

**预期响应：**
```
流式文本输出（Content-Type: text/plain; charset=utf-8）
内容会逐步返回，类似：
"#include <uart.h>\n\n"
"int main() {\n"
"    uart_init();\n"
...
```

**Postman 设置：**
- 在 Postman 中，流式响应会逐步显示
- 或者可以使用 Postman 的控制台查看实时输出

**测试要点：**
- 确认响应类型为 `text/plain`
- 确认内容逐步返回（流式）
- 适合生成较长的代码或文档

---

## 完整测试场景示例

### 场景 1: 完整工作流测试

1. **检查状态**
   ```
   GET /api/document/status
   ```

2. **重建索引（如需要）**
   ```
   POST /api/document/rebuild-index
   ```

3. **问答查询**
   ```
   POST /api/document/query
   Body: {"query": "PWM功能如何使用？", "mode": "qa", "k": 3}
   ```

4. **代码生成查询**
   ```
   POST /api/document/query
   Body: {"query": "生成一个PWM控制LED亮度的示例", "mode": "code", "k": 4}
   ```

5. **自动模式测试**
   ```
   POST /api/document/query
   Body: {"query": "线程如何创建和管理？", "mode": "auto", "k": 3}
   ```

### 场景 2: 错误处理测试

1. **空查询测试**
   ```json
   {
     "query": "",
     "mode": "qa",
     "k": 3
   }
   ```
   预期：返回 422 验证错误

2. **无效模式测试**
   ```json
   {
     "query": "测试查询",
     "mode": "invalid_mode",
     "k": 3
   }
   ```
   预期：返回相应错误

3. **k 值超出范围测试**
   ```json
   {
     "query": "测试查询",
     "mode": "qa",
     "k": 15
   }
   ```
   预期：返回 422 验证错误（k 应在 1-10 之间）

---

## Postman Collection 导入（可选）

可以创建 Postman Collection JSON 文件以便直接导入测试。以下是简要的 Collection 结构示例：

```json
{
  "info": {
    "name": "文档分析API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "获取索引状态",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "http://localhost:8000/api/document/status",
          "protocol": "http",
          "host": ["localhost"],
          "port": "8000",
          "path": ["api", "document", "status"]
        }
      }
    },
    {
      "name": "重建索引",
      "request": {
        "method": "POST",
        "header": [],
        "url": {
          "raw": "http://localhost:8000/api/document/rebuild-index",
          "protocol": "http",
          "host": ["localhost"],
          "port": "8000",
          "path": ["api", "document", "rebuild-index"]
        }
      }
    },
    {
      "name": "文档查询-问答",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"query\": \"如何使用GPIO驱动LED？\",\n  \"mode\": \"qa\",\n  \"k\": 3\n}"
        },
        "url": {
          "raw": "http://localhost:8000/api/document/query",
          "protocol": "http",
          "host": ["localhost"],
          "port": "8000",
          "path": ["api", "document", "query"]
        }
      }
    },
    {
      "name": "文档查询-代码生成",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"query\": \"生成一个LED闪烁的示例代码\",\n  \"mode\": \"code\",\n  \"k\": 4\n}"
        },
        "url": {
          "raw": "http://localhost:8000/api/document/query",
          "protocol": "http",
          "host": ["localhost"],
          "port": "8000",
          "path": ["api", "document", "query"]
        }
      }
    },
    {
      "name": "流式查询",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"query\": \"生成一个完整的UART通信示例\",\n  \"mode\": \"code\",\n  \"k\": 4\n}"
        },
        "url": {
          "raw": "http://localhost:8000/api/document/query/stream",
          "protocol": "http",
          "host": ["localhost"],
          "port": "8000",
          "path": ["api", "document", "query", "stream"]
        }
      }
    }
  ]
}
```

---

## 注意事项

1. **服务器启动**：确保 FastAPI 服务器已启动（`uvicorn app.main:app --reload`）

2. **Ollama 服务**：确保 Ollama 服务正在运行，并且已安装所需模型：
   - Embedding 模型：`nomic-embed-text`
   - 生成模型：`qwen3:8b`（或配置的其他模型）

3. **文档路径**：确保 `demos` 和 `drivers` 目录存在且包含文档文件

4. **首次运行**：首次使用时会自动构建索引，可能需要一些时间

5. **索引位置**：索引文件保存在 `docs_root/faiss_index` 目录下

---

## 常见问题排查

### 问题 1: 索引未加载
- **现象**：`index_loaded: false`
- **解决**：调用 `POST /api/document/rebuild-index` 重建索引

### 问题 2: 查询返回空结果
- **检查**：确认文档文件存在
- **检查**：确认索引已正确构建
- **检查**：尝试重建索引

### 问题 3: 流式查询不工作
- **检查**：确认请求头 `Content-Type` 设置正确
- **检查**：在 Postman 中可能需要切换到"Pretty"视图查看流式输出

### 问题 4: 模型调用失败
- **检查**：Ollama 服务是否运行
- **检查**：模型是否已安装（`ollama list`）
- **检查**：模型名称配置是否正确

---

## 测试检查清单

- [ ] 服务器正常启动
- [ ] Ollama 服务运行正常
- [ ] 索引状态检查通过
- [ ] 索引重建成功
- [ ] 问答模式查询正常
- [ ] 代码生成模式查询正常
- [ ] 自动模式检测正确
- [ ] 流式查询正常工作
- [ ] 错误处理正常（空查询、无效参数等）

