# Team API

基于 Sub2API 的内部 API 网关，成员人数不固定。

## 启动

需要 Docker、Docker Compose v2+ 和 Python 3.9+。在仓库根目录执行：

```sh
python3 team/team.py init --admin-email 你的管理员邮箱
python3 team/team.py start
```

Windows 将 `python3` 换成 `python`，并先启动 Docker Desktop。

默认访问 `http://localhost:8080`。管理员邮箱和随机密码保存在本地 `team/.env`。
服务器部署时重新执行 init 生成自己的密码；重复 init 不覆盖现有配置。

## 配置

编辑 `team/.env`，修改后重新执行 start：

| 参数 | 默认值 | 用途 |
|---|---|---|
| `BIND_HOST` | `127.0.0.1` | 监听地址；内网直接访问时可改为服务器内网 IPv4 地址或 `0.0.0.0` |
| `SERVER_PORT` | `8080` | 访问端口 |
| `DEFAULT_USER_CONCURRENCY` | `1` | 新成员默认并发；已有用户在后台调整 |
| `RUN_MODE` | `simple` | 内部简易模式，跳过站内余额扣费 |
| `SUB2API_IMAGE` | `ghcr.io/wei-shaw/sub2api:0.2.19` | 运行的应用镜像 |

后台接入 OpenAI 上游账号并完成授权，将账号绑定到 OpenAI 分组；按需创建成员，每人生成独立 Key 并选择对应分组。
客户端填写 `http://服务器地址:端口/v1` 和该成员的 Key，模型名称按账号实际支持填写。

可在后台自行调整站点设置；也可完成首次登录确认后执行以下命令，设置站点名称、关闭公开注册和支付入口：

```sh
python3 team/team.py configure
```

默认只监听本机；通过反向代理开放时配置 HTTPS，或通过内网访问并限制来源。数据库和 Redis 不对外发布端口。
账号、授权、密码和数据不进入仓库。管理员初始密码只在首次建库时生效，之后请在后台修改。

## 常用命令

```sh
python3 team/team.py status    # 查看服务状态
python3 team/team.py logs      # 查看应用日志
python3 team/team.py check     # 检查后台登录和服务，不调用上游模型
python3 team/team.py stop      # 停止服务，保留数据
```

来源：[Sub2API](https://github.com/Wei-Shaw/sub2api)，保留上游源码与 [LGPL-3.0 许可](LICENSE)。
