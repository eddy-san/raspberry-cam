#!/bin/bash
REMOTE_PATH="$1"
REMOTE_FILE="$2"
LOCAL_FILE="$3"

sshpass -p "${PASSWORD}" sftp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  "${REMOTE_USER}@${REMOTE_HOST}" <<EOF
cd ${REMOTE_PATH}
rm ${REMOTE_FILE}
put ${LOCAL_FILE} ${REMOTE_FILE}
bye
EOF

