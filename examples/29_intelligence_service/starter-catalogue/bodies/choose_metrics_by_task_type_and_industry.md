# Choose evaluation metrics by task type, class balance and industry

Pick the metrics that fit the shape of the task, name the metrics that mislead for this task, and add the conventions of the industry that will use the result.

## When to use it

Use it before training or comparing models, and whenever a result is reported with a single accuracy number.

## Steps

1. State the task type, the target shape, the class balance, the industry and whether a holdout set exists.
2. Choose by task type:
   - classification: area under the receiver operating characteristic curve. Unless the classes are stated to be imbalanced, add accuracy and the F1 score.
   - classification with a probability output: add logarithmic loss and a calibration measure such as the Brier score. A model can rank well and still be badly calibrated.
   - classification with imbalanced classes: add the area under the precision and recall curve, balanced accuracy, the F1 score and the Matthews correlation coefficient. Mark accuracy as misleading.
   - regression: root mean squared error, which penalizes large errors, mean absolute error, which is robust to outliers, and the coefficient of determination, which can be negative. Avoid mean absolute percentage error when targets approach zero.
   - ranking and search: normalized discounted cumulative gain, mean average precision, mean reciprocal rank or precision at k, because position matters.
   - forecasting: mean absolute scaled error against a naive forecast, symmetric mean absolute percentage error and root mean squared error, with a rolling origin backtest. A random split of a time series leaks the future.
   - text generation: reference based and human evaluation. Mark word overlap metrics such as BLEU and ROUGE as misleading when used alone.
   - detection: the area under the precision and recall curve, precision at a low false positive rate, and recall.
3. Add the industry convention:
   - clinical: sensitivity and specificity, predictive values at the operating threshold, and a confidence interval. A false negative usually costs most.
   - finance and trading: risk adjusted return, maximum drawdown and an out of sample walk forward backtest.
   - fraud and security: precision at a low false positive rate, because the base rate is tiny.
   - manufacturing: defect and escape rate, yield, and false rejects against false accepts.
   - marketing experiments: lift against a control group with a confidence interval.
4. Always add the health checks: the gap between training and cross-validated scores, a score that is too perfect, a baseline at chance level, and constant output.
5. When no holdout set exists, say that the honest estimate is unverified and reserve a sealed split first.

## Checks

- A binary, imbalanced classification task lists accuracy as misleading.
- Every recommended metric has a stated direction.
- The report names the holdout set or states that there is none.

## Known-wrong example

A fraud model reports 99 percent accuracy. In this illustration 99 percent of the transactions are legitimate, so a model that flags nothing reaches the same number. Accuracy says nothing about the minority class.

## What to record

- The stated task signals, the recommended and the misleading metrics, and the reasons.
- The industry convention that was applied.

## Source

- `src/loop_engine/code_nodes/measurement.py`: `select_measures`, `MeasurementSignals` and the conventions in `measurement_pack`.

Licence: MIT. Compiled from revision 4249eca.
