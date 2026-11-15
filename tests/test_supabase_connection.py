# -*- coding: utf-8 -*-
"""
Created on Sun Nov 15 16:00:26 2026

@author: mohak
"""


from api.integrations.supabase_client import (
    get_supabase_client,
)


def main():
    client = get_supabase_client()

    response = (
        client
        .table("chat_sessions")
        .select("id")
        .limit(1)
        .execute()
    )

    print("Supabase connection successful.")
    print("Accessible table: chat_sessions")
    print("Rows returned:", len(response.data))


if __name__ == "__main__":
    main()
