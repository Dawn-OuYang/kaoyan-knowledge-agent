#!/usr/bin/env bash

# Resolve the CANN environment installed by HiDevLab or a standard Ascend image.
resolve_ascend_env() {
  if [ -n "${ASCEND_ENV:-}" ] && [ -f "${ASCEND_ENV}" ]; then
    printf '%s\n' "${ASCEND_ENV}"
    return 0
  fi

  local candidate
  for candidate in \
    /usr/local/Ascend/ascend-toolkit/set_env.sh \
    /usr/local/Ascend/cann/set_env.sh \
    /usr/local/Ascend/cann-9.0.0/set_env.sh \
    /usr/local/Ascend/ascend-toolkit/latest/set_env.sh; do
    if [ -f "${candidate}" ]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done

  candidate="$(find /usr/local/Ascend -maxdepth 3 -name set_env.sh -type f 2>/dev/null | head -n 1)"
  if [ -n "${candidate}" ]; then
    printf '%s\n' "${candidate}"
    return 0
  fi

  return 1
}

source_ascend_env() {
  local resolved
  if ! resolved="$(resolve_ascend_env)"; then
    echo "ERROR: unable to locate an Ascend CANN set_env.sh" >&2
    return 1
  fi
  export ASCEND_ENV="${resolved}"
  # shellcheck disable=SC1090
  source "${ASCEND_ENV}"
  echo "Using CANN environment: ${ASCEND_ENV}"
}
