#!/bin/bash

. .env

# through gateway
curl http://localhost:3000   -H "Content-Type: application/json"   -H "Authorization: Bearer $ANTHROPIC_API_KEY"   -d '
{
    "model": "sonnet-4",
    "messages": [
      {
        "role": "system",
        "content": "You are a helpful assistant."
      },
      {
        "role": "user",
        "content": "Is 123-45-6789 a valid SSN"
      }
    ]
  }'
