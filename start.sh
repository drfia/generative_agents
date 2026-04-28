#!/bin/bash
# Generative Agents 一键启动脚本

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/venv/bin/python"
STEPS="${1:-100}"

# 停止已有进程
pkill -f "manage.py runserver" 2>/dev/null
pkill -f "reverie.py" 2>/dev/null
sleep 1

echo "=== [1/2] 启动前端服务器 ==="
cd "$ROOT/environment/frontend_server"
"$VENV" manage.py runserver --noreload > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!

# 等待前端就绪
for i in $(seq 1 10); do
  sleep 1
  if curl -s http://localhost:8000/ | grep -q "environment server"; then
    echo "    前端已就绪: http://localhost:8000"
    break
  fi
done

echo ""
echo "=== [2/2] 启动模拟服务器 (${STEPS} 步) ==="
echo "    浏览器访问: http://localhost:8000/simulator_home"
echo ""
cd "$ROOT/reverie/backend_server"
"$VENV" reverie.py --auto "$STEPS"

# 退出时停止前端
kill $FRONTEND_PID 2>/dev/null
