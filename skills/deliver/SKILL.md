---
name: deliver
description: Use when the operator hands the PR this session is working on to someone for review (manda pro fulano revisar, entrega pro fulano, pede review pro fulano, deliver to someone), or invokes `/deliver <person>`. Takes that one PR, marks it ready for review, requests the person as reviewer on GitHub and sends them a Slack message asking for the review. Never picks a PR from a list of open ones.
---

# deliver

```
/deliver <person> [-- note for the message]
```

Three things, in this order, on **the PR of this conversation**:

1. Mark it ready for review.
2. Request `<person>` as reviewer.
3. Send `<person>` a Slack message asking for the review.

Invoking authorizes all three, including sending the Slack message. No confirmation gate.

**The conversation comes first.** Everything this skill needs (which PR, who the person is, what the PR does, where to send the message, what to say) is usually already in the conversation. Use it. Run a lookup only for what the conversation does not answer.

## 1. Resolve

**The PR.** The one this session has been working on: a number, URL or branch named earlier, or the PR opened in this conversation. If the conversation names none, `gh pr view --json number,url,title,isDraft,headRefOid` on the current branch. Never list open PRs and pick one. No PR: ask. When this conversation worked on two PRs together (a pair across repos), deliver both, in one message.

If the local branch has commits the PR head does not (`git status -sb` shows `ahead`), stop and say so: the reviewer would read stale code.

**The GitHub login.** From the conversation, else:

```bash
gh api graphql -F owner='{owner}' -F name='{repo}' -F q='<person>' \
  -f query='query($owner:String!,$name:String!,$q:String!){repository(owner:$owner,name:$name){assignableUsers(first:5,query:$q){nodes{login name}}}}'
```

**The Slack user.** `slack_search_users` with the person's name as keywords. Its id is the DM channel.

More than one match on either side: ask, with the candidates as options.

## 2. Do

```bash
gh pr ready <number>                         # already ready is fine
gh pr edit <number> --add-reviewer <login>
```

Then `slack_send_message` with `channel_id` = the person's Slack id. If the conversation named a channel or thread instead, send it there and mention the person (`<@USER_ID>`).

The message is **pt-BR**, because it goes to a pt-BR teammate (the plugin's "content published elsewhere" exception; do not translate it). It copies how the operator writes review requests by hand, in three parts:

1. A sentence asking the person to review, ending in `:`.
2. A bullet list of the PR URLs, **a list even with one PR**.
3. Below it, the context of the PR in a few plain lines: what it is for and why it exists, plus anything that changes how to review it (merge order, how deep to look).

```
Nathan, consegue revisar essas duas PRs:
• https://github.com/virtual360-io/aboard/pull/88
• https://github.com/virtual360-io/vquick/pull/30

São do Vquick e do Aboard, para a gente conseguir implementar uma integração boa entre o Vmanager (que roda dentro do Vquick) e o Aboard.
A do Aboard vai primeiro, porque tem migração.
```

- **The URL is bare.** Never `[title](url)` and never a title as the link text: it renders as a long blue sentence. Send with `unfurl_app_links: true`, so the GitHub preview carries the title.
- **The context comes from the conversation**, said the way the operator would say it to a teammate. Not a summary of the PR body, not a list of files. A `-- note` from the invocation goes into it.
- **No filler.** No "Oi", no "Te coloquei como revisor", no CI status, no thanks, no emoji.
- Never add the "O envio foi feito usando Claude" line: Slack appends it.

## 3. Report

The PR URL, the reviewer requested, and the Slack message permalink. A step that failed (the person is the PR author, no Slack match) is reported as failed, and the other steps still run.
