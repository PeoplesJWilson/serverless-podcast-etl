#!/bin/bash

if [ $# -ne 1 ]; then
  echo "Usage: $0 <message>"
  exit 1
fi

queue_url=$(aws sqs get-queue-url --queue-name "podcast-download-queue.fifo" --output "text")  # Replace with your SQS queue URL
message="$1"

current_time=$(date +%s)
aws sqs send-message --queue-url "$queue_url" --message-body "$message" --message-group-id "podcast-names" --message-deduplication-id "$current_time"

