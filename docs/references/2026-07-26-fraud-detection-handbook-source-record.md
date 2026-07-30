# Fraud Detection Handbook source record

**Retrieved:** 26 July 2026  
**Purpose:** attribution and design trace for the independently implemented S0 synthetic operational case study

## Official source

- Yann-Aël Le Borgne, Wissam Siblini, Bertrand Lebichot, and Gianluca Bontempi (2022), *Reproducible Machine Learning for Credit Card Fraud Detection - Practical Handbook*, Université Libre de Bruxelles.
- Repository: https://github.com/Fraud-Detection-Handbook/fraud-detection-handbook
- Online book: https://fraud-detection-handbook.github.io/fraud-detection-handbook/
- Simulator chapter: https://fraud-detection-handbook.github.io/fraud-detection-handbook/Chapter_3_GettingStarted/SimulatedDataset.html
- Feature-transformation chapter: https://fraud-detection-handbook.github.io/fraud-detection-handbook/Chapter_3_GettingStarted/BaselineFeatureTransformation.html

The official README states that notebook code is released under GNU GPL v3.0 and prose and pictures under CC BY-SA 4.0. The local S0 generator is an independent implementation informed by the documented concepts. No handbook notebook code is copied into this repository.

## Retrieved source hashes

| Retrieved source | SHA-256 |
|---|---|
| Official simulated-dataset notebook | `3906c037f9652fb390bfb57d84e50235d3f4669456c9939000411494797b9785` |
| Official baseline-feature-transformation notebook | `845007d92018e84ce6e828ff5bd4e7c1ee16623c838bc9421355282244c1f04c` |

## Concepts adapted, not copied

- deterministic synthetic customer and terminal profiles;
- chronological transaction generation;
- injected fraud scenarios involving unusual transaction behaviour and compromised terminals;
- customer activity features over recent time windows;
- terminal activity and delayed fraud-risk features;
- chronological evaluation appropriate to a transaction stream.

The local implementation adds its own generator, feature catalogue, model contract, manifest format, structured explanation comparison, deterministic validator, and React/FastAPI workbench integration.
