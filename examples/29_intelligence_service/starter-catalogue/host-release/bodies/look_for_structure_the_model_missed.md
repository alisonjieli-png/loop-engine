# Look for structure that the model missed

Question a fitted model the way an experienced reviewer would: look at what is left over after the fit, and at the structure in the raw data that the model does not use.

## When to use it

Use it after a first model works and before tuning it further, and whenever a score has stopped improving.

## Steps

1. Residual patterns: ask whether there are patterns in the residuals, which means structure that the model failed to capture. Plot the residuals against the fitted values and against each feature, and test for non-randomness.
2. Changing variance: ask whether the variance of the residuals changes across the range. Use a Breusch-Pagan or White test, or compare the spread of the residuals by bin.
3. Dependence in time or space: ask whether the residuals are autocorrelated. Use the Durbin-Watson statistic or the autocorrelation function of the residuals.
4. Clusters: ask whether the raw data holds clusters that could mean something the model is not using. Run an unsupervised clustering, measure it with the silhouette score, and compare cluster membership with the errors.
5. Hidden variables: ask whether there are latent variables or interactions that the model does not detect. Use factor analysis or principal component analysis, test engineered interactions, and ask for candidate confounders.
6. Testing for the unseen: ask how a hidden pattern could be tested at all. Hold out a structured subset, train a probe on the residuals, and look for residual structure that can be learned.
7. Mark each question as answerable by code or as needing judgment. A question that code can answer is a candidate for a reusable function.

## Checks

- Every question has a computed answer or a stated reason why it could not be computed.
- A probe trained on the residuals that predicts better than chance means that structure remains.
- The findings are tested on data that did not shape them.

## Known-wrong example

A team tunes the settings of a sales model for a week and gains almost nothing. A plot of the residuals by calendar week shows a clear wave: the model has no feature for school holidays. One look at the residuals was worth more than the week of tuning.

## What to record

- Each question, the analysis that answered it and the result.
- Every structure that was found, with its size and the data it was tested on.
- The questions that code can answer, as candidates for reusable functions.

## Source

- `src/loop_engine/strings/interrogation.py`: the question bank, categories `residual_analysis` and `latent_structure`, each with its way of answering and whether code can answer it.

Licence: MIT. Compiled from revision 379c271.
