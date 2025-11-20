# Exec Dir MCP

一个基于 Model Context Protocol (MCP) 的命令执行服务器，支持在指定目录中安全地执行命令。

## 功能特性

- 🎯 **安全执行**：支持配置允许的目录列表，防止在未授权目录执行命令
- 📁 **灵活配置**：可设置默认工作目录，支持在任意允许的目录执行命令
- ⏱️ **超时控制**：支持自定义命令执行超时时间
- 🔄 **异步执行**：基于 asyncio 的异步命令执行，性能优异
- 📊 **详细日志**：完整的执行日志记录，方便调试和监控
- 🛡️ **目录验证**：自动验证目录存在性和权限

## 安装

### 系统要求

- Python >= 3.13
- uv (推荐) 或 pip

### 使用 uv 安装

```bash
# 克隆仓库
git clone https://github.com/yunhai-dev/exec-dir-mcp.git
cd exec-dir-mcp

# 安装依赖
uv sync

# 开发模式安装
uv pip install -e .
```

### 使用 pip 安装

```bash
pip install -e .
```

## MCP 客户端配置

### Claude Desktop 配置

在你的 `claude_desktop_config.json` 中添加以下配置：

```json
{
  "mcpServers": {
    "exec-dir-mcp": {
      "command": "uvx",
      "args": ["exec-dir-mcp"]
    }
  }
}
```

#### 安全配置示例

**基本配置（允许所有目录）：**
```json
{
  "mcpServers": {
    "exec-dir-mcp": {
      "command": "uvx",
      "args": ["exec-dir-mcp"]
    }
  }
}
```

**安全配置（限制可访问目录）：**
```json
{
  "mcpServers": {
    "exec-dir-mcp": {
      "command": "uvx",
      "args": [
        "exec-dir-mcp",
        "--dir", "/home/user/projects",
        "--allowed", "/home/user/projects",
        "--allowed", "/tmp"
      ]
    }
  }
}
```

**多项目工作区配置：**
```json
{
  "mcpServers": {
    "exec-dir-mcp": {
      "command": "uvx",
      "args": [
        "exec-dir-mcp",
        "--dir", "/workspace",
        "--allowed", "/workspace/project1",
        "--allowed", "/workspace/project2",
        "--allowed", "/workspace/shared"
      ]
    }
  }
}
```

### 其他 MCP 客户端配置

#### UVX 方式（推荐）

使用 uvx 直接运行（最简单，无需安装）：

```json
{
  "mcpServers": {
    "exec-dir-mcp": {
      "command": "uvx",
      "args": [
        "exec-dir-mcp",
        "--dir", "/workspace",
        "--allowed", "/workspace"
      ]
    }
  }
}
```

#### 直接命令方式

如果你已经安装了包（`pip install` 或 `uv add`），可以直接使用：

```json
{
  "mcpServers": {
    "exec-dir-mcp": {
      "command": "exec-dir-mcp",
      "args": [
        "--dir", "/workspace",
        "--allowed", "/workspace"
      ]
    }
  }
}
```

### 配置说明

- **command**:
  - `uvx exec-dir-mcp`: 使用 uvx 直接运行（推荐，最简单）
  - `exec-dir-mcp`: 已安装包后的直接命令
- **args**: 启动参数
  - `--dir`: 指定默认工作目录
  - `--allowed`: 指定允许访问的目录（可多次使用）

### 配置方式对比

| 方式 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| `uvx exec-dir-mcp` | ✅ 无需安装<br/>✅ 最简单 | ❌ 需要 uv | 推荐使用 |
| `exec-dir-mcp` | ✅ 已安装后直接使用 | ❌ 需要先安装包 | 已在环境中安装 |

### 配置文件位置

- **Claude Desktop**:
  - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
  - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
  - Linux: `~/.config/Claude/claude_desktop_config.json`

## 使用方法

### 作为 MCP 服务器运行

#### 基本用法

```bash
# 使用 uvx（推荐）
uvx exec-dir-mcp

# 使用已安装的命令
exec-dir-mcp

# 使用模块方式
python -m exec_dir_mcp.main

# 指定默认目录
uvx exec-dir-mcp --dir /home/user/projects

# 指定默认目录和允许的目录列表
uvx exec-dir-mcp \
  --dir /home/user/projects \
  --allowed /home/user/projects \
  --allowed /tmp
```

#### 命令行参数

- `--dir`：默认工作目录（默认：当前目录）
- `--allowed`：允许执行命令的目录（可多次指定，不指定则允许所有目录）

#### 示例

```bash
# 在项目目录中运行，允许访问项目目录和临时目录
uvx exec-dir-mcp \
  --dir /home/user/my-project \
  --allowed /home/user/my-project \
  --allowed /tmp

# 安全模式：只允许特定目录
uvx exec-dir-mcp \
  --dir /safe/workspace \
  --allowed /safe/workspace/project1 \
  --allowed /safe/workspace/project2
```

### 在代码中使用

```python
import asyncio
from exec_dir_mcp.main import MCPServer

async def main():
    # 创建服务器实例
    server = MCPServer(
        default_dir="/home/user/projects",
        allowed_dirs=["/home/user/projects", "/tmp"]
    )

    # 运行服务器
    await server.run()

asyncio.run(main())
```

## MCP 工具

### execute_command

在指定目录中执行命令。

#### 参数

- `command` (string, 必需)：要执行的 shell 命令
- `working_dir` (string, 可选)：工作目录（默认使用配置的默认目录）
- `timeout` (integer, 可选)：超时时间，单位秒（默认：30）

#### 返回值

```json
{
  "success": true,
  "stdout": "命令标准输出",
  "stderr": "命令标准错误输出",
  "returncode": 0,
  "working_dir": "/执行目录",
  "command": "执行的命令"
}
```

#### 错误响应

```json
{
  "success": false,
  "error": "错误描述"
}
```

#### 使用示例

```python
# 通过 MCP 客户端调用
result = await client.call_tool("execute_command", {
    "command": "ls -la",
    "working_dir": "/home/user/projects",
    "timeout": 10
})
```

## 项目结构

```
exec-dir-mcp/
├── README.md                 # 项目文档
├── pyproject.toml           # 项目配置
├── .gitignore              # Git 忽略文件
├── .python-version         # Python 版本
├── src/
│   └── exec_dir_mcp/
│       ├── __init__.py      # 包初始化
│       ├── main.py          # 主程序逻辑
│       └── py.typed         # 类型提示标记
```

## 协议支持

- **MCP 版本**：2024-11-05
- **JSON-RPC**：2.0
- **传输协议**：标准输入/输出

## 安全说明

1. **目录限制**：强烈建议在生产环境中配置 `--allowed` 参数限制可访问的目录
2. **命令执行**：服务器会执行传入的任意 shell 命令，请确保客户端输入的安全性
3. **超时保护**：默认 30 秒超时，可通过 `timeout` 参数调整
4. **路径验证**：自动验证目录存在性和权限

## 开发

### 运行测试

```bash
uv run pytest
```

### 代码格式化

```bash
uv run ruff format .
uv run ruff check .
```

## 许可证

MIT License

## 作者

YunHai <yunhai@yhnotes.com>

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v1.0.2

- 初始版本
- 支持基本的命令执行功能
- 支持目录权限控制
- 支持超时配置
- 完善文档和配置说明
