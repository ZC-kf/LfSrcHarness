#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INSTALL_ROOT="${SOURCE_ROOT}"
CHECK_ONLY=0
INSTALL_DEPS=0
COPY_ONLY=0

usage() {
  printf 'Usage: bash "%s" [--root DIRECTORY] [--check] [--install-deps] [--copy-only]\n' "$0"
}

while (( $# > 0 )); do
  case "$1" in
    --root)
      if (( $# < 2 )); then usage; exit 2; fi
      INSTALL_ROOT="$2"
      shift 2
      ;;
    --check) CHECK_ONLY=1; shift ;;
    --install-deps) INSTALL_DEPS=1; shift ;;
    --copy-only) COPY_ONLY=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) usage; exit 2 ;;
  esac
done

copy_source() {
  local item
  local directories=(src docs plugins/examples plugins/template deploy/ansible
    deploy/k8s deploy/systemd deploy/windows web/src)
  local files=(pyproject.toml uv.lock README.md LICENSE.md
    plugins/scope.example.yaml deploy/.env.example deploy/Dockerfile
    deploy/Vagrantfile deploy/config/config.yaml deploy/config/scope.yaml
    deploy/desktop_entry.py deploy/docker-compose.yml deploy/install.ps1
    deploy/install.sh deploy/pyinstaller_entry.py web/index.html web/package.json
    web/package-lock.json web/tsconfig.app.json web/tsconfig.json
    web/tsconfig.node.json web/vite.config.ts)
  if [[ "${INSTALL_ROOT}" == "${SOURCE_ROOT}" ]]; then return 0; fi
  if [[ -d "${SOURCE_ROOT}/web/dist" ]]; then directories+=(web/dist); fi
  for item in "${directories[@]}" "${files[@]}"; do
    if [[ ! -e "${SOURCE_ROOT}/${item}" ]]; then continue; fi
    mkdir -p "${INSTALL_ROOT}/$(dirname "${item}")"
    cp -a "${SOURCE_ROOT}/${item}" "${INSTALL_ROOT}/${item}"
  done
}

if (( COPY_ONLY )); then
  copy_source
  exit 0
fi

find_python() {
  local candidate
  if [[ -n "${LFSRC_PYTHON_BIN:-}" ]]; then
    candidate="${LFSRC_PYTHON_BIN}"
  else
    candidate="$(command -v python3.12 || true)"
  fi
  if [[ -n "${candidate}" ]] && "${candidate}" -c \
    'import sys, venv, ensurepip; assert sys.version_info[:2] == (3, 12)' >/dev/null 2>&1; then
    PYTHON_BIN="${candidate}"
    return 0
  fi
  return 1
}

needs_node() {
  [[ ! -f "${SOURCE_ROOT}/web/dist/index.html" ]]
}

check_prerequisites() {
  local missing=0
  if [[ "$(uname -s)" != "Linux" ]]; then
    printf 'This installer supports Linux/Kali only. Use the Windows setup on Windows.\n'
    return 1
  fi
  if ! find_python; then
    printf '缺少 Python 3.12（含 venv）。请安装后重试，或使用 --install-deps 尝试通过 apt 安装。\n'
    missing=1
  fi
  if needs_node && ! command -v npm >/dev/null 2>&1; then
    printf '缺少 npm：当前源码未包含已编译界面。请安装 Node.js/npm，或使用带 web/dist 的发行包。\n'
    missing=1
  fi
  if (( missing )); then
    printf '安装前检查未通过；补齐环境后再次运行本脚本即可继续。\n'
    return 1
  fi
  printf '安装前检查通过：Python 3.12 可用，界面资源可用或可构建。\n'
}

install_apt_prerequisites() {
  local packages=()
  local elevated=()
  if ! command -v apt-get >/dev/null 2>&1; then
    printf '自动补齐仅支持 apt 系发行版。请按发行版文档安装 Python 3.12/venv 和 Node.js/npm。\n'
    return 1
  fi
  if (( EUID != 0 )); then
    if ! command -v sudo >/dev/null 2>&1; then
      printf '需要管理员权限安装系统组件；请安装 sudo 或请管理员补齐环境。\n'
      return 1
    fi
    elevated=(sudo)
  fi
  "${elevated[@]}" apt-get update
  if ! find_python; then
    if ! apt-cache show python3.12 >/dev/null 2>&1 ||
      ! apt-cache show python3.12-venv >/dev/null 2>&1; then
      printf '当前 apt 仓库没有 Python 3.12/venv。请先配置可信仓库或手动安装 Python 3.12，再重新运行。\n'
      return 1
    fi
    packages+=(python3.12 python3.12-venv)
  fi
  if needs_node && ! command -v npm >/dev/null 2>&1; then
    packages+=(nodejs npm)
  fi
  if (( ${#packages[@]} == 0 )); then return 0; fi
  printf '将通过系统软件源安装：%s\n' "${packages[*]}"
  "${elevated[@]}" apt-get install -y "${packages[@]}"
}

if ! check_prerequisites; then
  if (( CHECK_ONLY )); then exit 1; fi
  if (( ! INSTALL_DEPS )) && [[ -t 0 ]]; then
    read -r -p '是否通过系统软件源自动补齐缺失组件？[y/N] ' answer
    if [[ "${answer}" == "y" || "${answer}" == "Y" ]]; then INSTALL_DEPS=1; fi
  fi
  if (( ! INSTALL_DEPS )); then exit 1; fi
  install_apt_prerequisites
  check_prerequisites
fi
if (( CHECK_ONLY )); then exit 0; fi

if needs_node; then
  (cd "${SOURCE_ROOT}/web" && npm ci && npm run build)
fi

copy_source

if ! "${PYTHON_BIN}" -m venv "${INSTALL_ROOT}/.venv"; then
  printf '无法创建 Python 虚拟环境。请安装 python3.12-venv 后重新运行。\n' >&2
  exit 1
fi
"${INSTALL_ROOT}/.venv/bin/python" -m pip install --upgrade pip
"${INSTALL_ROOT}/.venv/bin/python" -m pip install "${INSTALL_ROOT}"

mkdir -p "${INSTALL_ROOT}/runs" "${INSTALL_ROOT}/package"
if [[ ! -f "${INSTALL_ROOT}/deploy/.env" ]]; then
  cp "${INSTALL_ROOT}/deploy/.env.example" "${INSTALL_ROOT}/deploy/.env"
fi
printf 'LfSrcHarness installed at %s\n' "${INSTALL_ROOT}"
