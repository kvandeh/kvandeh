---
title: 95% Accurate, Useless at Parties
summary: Bouncer filters Spotify Jam requests with a language model. It scored 95.2% on an evaluation set, but failed at real parties.
author: Kieran van der Heijde
avatar: assets/kieran.jpg
date: 2026-11-10
---

[Bouncer](https://github.com/kvandeh/Bouncer) filters song requests in a Spotify Jam. The host writes a rule, for example "energetic, no rap", and Bouncer decides which requests go into the queue.

## The missing data

Earlier tools of this type used Spotify audio features: tempo, energy and valence. Spotify removed this data for new applications. Without it, a tool knows nothing about the sound of a song.

## Method

Bouncer uses the cultural knowledge of a language model in place of audio data. It converts a description of each track (artists, genres, Last.fm tags) into an embedding. A similarity score accepts or rejects the track. For uncertain cases, a language model makes the decision:

```python
score = 0.7 * cosine_similarity + 0.2 * tag_overlap + 0.1 * audio_match

if score > 0.55:
    accept(track)
elif score < 0.15:
    reject(track)
else:
    ask_llm_judge(track)   # cached per (instruction, track)
```

## Results

On 963 labelled tracks, Bouncer reached 95.2% accuracy. But the model knows popular songs, because many texts describe them. It knows little about less popular songs, and at a party many requests are less popular. Thus real accuracy was lower than the evaluation figure.

## Conclusion

A language model knows text about music, not the music itself. A song with no text about it is unknown to the model. The most promising next step is CLAP, a model that makes embeddings directly from audio.
