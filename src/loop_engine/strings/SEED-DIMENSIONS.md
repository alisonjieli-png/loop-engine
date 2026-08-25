# Seed Dimensions — the curated banks the foundry composes into seeds

Owner-curated generation dimensions for the self-improvement practitioner.
A SEED = a composition across these banks (persona × operator × target ×
situation × era × …). The banks below hold ~350 curated entries; the
composition space exceeds 10,000,000 distinct seeds, and
`string_foundry.compose_seeds(n)` materializes any n of them
deterministically (seeded). Bank size is a SEARCH SPACE, not a per-task
quota. Every generated string stays a candidate until it wins on real
tasks.

Format: one entry per line under each `##` heading. Lines starting with
`#` or blank are ignored by the loader.

## personas_jobs
senior data scientist
ml engineer
data engineer
statistician
econometrician
biostatistician
actuary
quantitative trader
risk officer
fraud investigator
site reliability engineer
security engineer
database administrator
compiler engineer
embedded systems engineer
distributed systems engineer
performance engineer
product manager
project manager
operations researcher
supply chain analyst
epidemiologist
clinical trial designer
survey methodologist
experimental physicist
control systems engineer
signal processing engineer
computer vision engineer
nlp engineer
recommender systems engineer
search relevance engineer
forecasting analyst
demand planner
credit risk modeler
insurance underwriter
geospatial analyst
remote sensing scientist
bioinformatician
computational chemist
astronomer
meteorologist
seismologist
auditor
forensic accountant
investigative journalist
intelligence analyst
chess grandmaster
poker professional
emergency room triage physician
air traffic controller
submarine sonar operator
archaeologist
patent examiner
referee of a scientific journal

## famous_scientists
Richard Feynman
John Tukey
George Box
Ronald Fisher
Florence Nightingale
Claude Shannon
Alan Turing
John von Neumann
Andrey Kolmogorov
Judea Pearl
David Cox
C. R. Rao
Grace Hopper
Barbara Liskov
Donald Knuth
Edsger Dijkstra
Leslie Lamport
Marie Curie
Charles Darwin
Gregor Mendel
Santiago Ramón y Cajal
Barbara McClintock
Rosalind Franklin
Katherine Johnson
Emmy Noether
Henri Poincaré
Carl Friedrich Gauss
Pierre-Simon Laplace
Thomas Bayes
Daniel Kahneman
Amos Tversky
Herbert Simon
Elinor Ostrom
W. Edwards Deming
Genichi Taguchi
Frederick Brooks
Fisher Black
Benoit Mandelbrot
Norbert Wiener
Ada Lovelace

## famous_authors_thinkers
George Orwell
Jorge Luis Borges
Ursula K. Le Guin
Italo Calvino
Anton Chekhov
Leo Tolstoy
Mary Shelley
Jonathan Swift
Michel de Montaigne
Seneca
Marcus Aurelius
Sun Tzu
Niccolò Machiavelli
Karl Popper
Thomas Kuhn
Ludwig Wittgenstein
David Hume
John Stuart Mill
Hannah Arendt
Simone de Beauvoir
Charles Sanders Peirce
William of Ockham
Nassim Nicholas Taleb
Atul Gawande
Richard Hamming

## geographies
Japan
South Korea
India
Indonesia
Vietnam
China
Brazil
Argentina
Mexico
Nigeria
Kenya
Egypt
South Africa
Germany
France
United Kingdom
Nordics
Baltics
Poland
Turkey
Israel
Saudi Arabia
United Arab Emirates
rural United States
American Midwest
Appalachia
Silicon Valley
rust-belt manufacturing towns
Arctic research stations
small island nations
megacity informal settlements
cross-border trade corridors
subsistence farming regions
monsoon-dependent agriculture belts
high-altitude communities

## time_frames
pre-industrial 1700s
Victorian 1870s
early telephony 1910s
wartime rationing 1940s
mainframe era 1960s
oil crisis 1970s
personal computing 1980s
early internet 1995
dot-com crash 2001
smartphone adoption 2010
deep learning boom 2015
pandemic disruption 2020
post-LLM 2024
five years from now
twenty years from now
a world without cheap compute
a world with free inference
a world with strict data-privacy law everywhere
quarterly-earnings horizon
century-long infrastructure horizon

## situations
a deadline in four hours
a dataset that arrives 10x larger than promised
labels produced by three annotators who disagree
a metric the stakeholder chose but cannot defend
a model that must run on a phone
a pipeline that silently dropped 3% of rows last month
an incumbent solution nobody understands anymore
a regulator demanding an explanation for every prediction
a competitor who ships twice as fast with worse accuracy
training data that ends before a major world event
a target that changes definition halfway through the project
a demo tomorrow to a skeptical executive
zero budget for external services
one GPU for a team of ten
a leaked test set someone already trained on
a domain expert who distrusts every model output
a legacy SQL job that must keep running during migration
a cold-start product with no historical data
an on-call rotation drowning in false-positive alerts
a spreadsheet that IS the production system
a customer who wants the model yesterday and perfect
an acquisition freezing all infrastructure changes
a dataset with personally identifiable information sprinkled through free text
a benchmark everyone games and nobody trusts
the day after a silent schema change
an experiment whose control group got contaminated
a hypothesis the team is emotionally invested in
a vendor API that changes behavior without notice
data collected only from users who did not churn
a fraud pattern that adapts to every new rule
the first week after a big-bang rewrite
a model whose errors cluster on the most valuable customers
a leadership request to "just add AI"
an inherited codebase with no tests
a migration that must not lose a single record
peak-season traffic at 20x baseline
a postmortem where nobody agrees on the root cause
an annotation budget for exactly 500 labels
two teams maintaining rival versions of the truth
a compliance freeze one week before launch

## thinking_operators
observe
detect
explain
decompose
compare
rank
eliminate
falsify
invert
contradict
perturb
ablate
cluster
simulate
counterfactually change
analogize
transfer
triangulate
stress-test
combine
ensemble
compress
generalize
localize
trace
predict
audit

## targets
goal
assumption
raw data
labels
missingness
splits
features
representation
model
hyperparameters
predictions
residuals
uncertainty
subgroups
metric
evaluator
pipeline
code
graph
tool
artifact
runtime
cost
failure
recovery
human process
commit history
research literature
data collection process
deployment boundary

## contrasts
best versus worst
expected versus observed
common versus rare
stable versus unstable
general versus subgroup
fast versus accurate
cheap versus expensive
current method versus prohibited method
current assumption versus reversed assumption
champion versus intentionally diverse alternative

## domains
credit scoring
insurance pricing
medical diagnosis
drug discovery
clinical operations
epidemiology
fraud detection
anti-money laundering
algorithmic trading
supply chain forecasting
demand planning
dynamic pricing
recommendation systems
search ranking
ad auctions
churn prevention
customer lifetime value
predictive maintenance
industrial quality control
agriculture yield prediction
energy load forecasting
grid anomaly detection
climate modeling
satellite imagery analysis
autonomous driving perception
robotics control
speech recognition
machine translation
document extraction
legal discovery
patent analysis
cybersecurity intrusion detection
spam filtering
content moderation
A/B testing platforms
educational assessment
sports analytics
elections forecasting
real estate valuation
logistics routing

## data_regimes
ten rows per class
a million rows with five useful columns
wide data with more features than rows
heavily imbalanced 1:10000 classes
streaming data that never stops
panel data with entities entering and leaving
hierarchical data three levels deep
censored survival times
mixed text tables and images
graphs with communities and bridges

## failure_regimes
silent data drift
target leakage discovered late
duplicate entities across splits
a feature computed from the future
overfitting hidden by a lucky split
underfitting disguised as regularization
metric mismatch with the business goal
feedback loops from the model's own decisions
annotation guidelines that shifted mid-project
a retrained model quietly worse on a minority slice
concept drift after a policy change
a cache serving stale predictions
seed-dependent results presented as robust
an ensemble hiding one broken member
evaluation on data the model indirectly saw
