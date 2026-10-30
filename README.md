# Team API

基于 [Sub2API](https://github.com/Wei-Shaw/sub2api) 的团队内部 API 网关部署配置。
成员人数不固定，每位成员使用独立用户和 Key；不内置 GPT 账号、OAuth 凭据或真实 API Key。

## 服务器部署

准备 Docker Engine、Docker Compose v2+ 和 Python 3.9+，然后在仓库根目录执行：

```sh
python3 team/team.py init --admin-email 你的管理员邮箱
python3 team/team.py validate
python3 team/team.py start
python3 team/team.py check
```

Windows 使用 `python` 替换 `python3`，并先启动 Docker Desktop。

初始只监听本机 `127.0.0.1:8080`，服务器可通过 SSH 隧道访问：

```sh
ssh -L 8080:127.0.0.1:8080 你的服务器用户名@服务器地址
```

浏览器打开 `http://localhost:8080`，从服务器本地的 `team/.env` 获取管理员密码。
首次登录如出现项目自身的使用确认，由管理员阅读并完成，然后执行：

```sh
python3 team/team.py configure
```

这会设置站点名称、关闭公开注册和支付入口，默认每位新成员并发为 1。不会限制成员总数。

接下来由账号持有人在后台接入上游账号，将它绑定到 OpenAI 分组，先设账号总并发为 2，测试后调整。
管理员为成员新增用户，成员创建独立 Key 并选择对应 OpenAI 分组。真实模型调用必须等上游授权后验证。

完整的服务器交接、内网接入和备份说明见 [team/README.md](team/README.md)。
上游原始说明见 [README.upstream.md](README.upstream.md) 和 [README_CN.md](README_CN.md)。

## 来源与许可

本仓库保留 Sub2API 源码快照、版权声明和 [LGPL-3.0 许可证](LICENSE)。
来源提交：`d851a38`（2026-10-30 拉取）；默认运行上游正式发布镜像 `ghcr.io/wei-shaw/sub2api:0.2.19`。
部署配置没有修改模型请求逻辑。上游服务的账号授权和使用条件仍然适用。

部署验证记录见 [team/VERIFICATION.md](team/VERIFICATION.md)。上游原始工作流全部保留；本仓库新增团队部署配置检查。
