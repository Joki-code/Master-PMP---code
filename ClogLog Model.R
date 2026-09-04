# =============================================================================
# Complete Script: Discrete-Time Survival Model (Complementary Log-Log)
# Uses EGID as building identifier.
# With regular standard error
# Exclusion of category == 2,
# with city-level covariates: VPI and Vote (numeric)
# Recodes 98/99 in clean_status to NA (missing) – drops the problematic row
# and the following year (due to unknown lag).
#
# REVISED: 
#   - Fixed tidy() error by using coeftable()
#   - Fixed print error by removing invalid 'n = Inf' argument
# =============================================================================

# -----------------------------------------------------------------------------
# 0. USER CONFIGURATION
# -----------------------------------------------------------------------------
data_path <- "xxx"

# Reference levels (set to NULL for automatic selection)
year_ref <- NULL
subsidy_ref <- "0"
gbaups_ref <- NULL
getyp_ref <- NULL
gkats_ref <- NULL
type_ville_ref <- NULL

# -----------------------------------------------------------------------------
# Load libraries
# -----------------------------------------------------------------------------
library(tidyverse)
library(forcats)
library(fixest)
library(modelsummary)
library(lmtest)
library(marginaleffects)   # for ATE with standard errors

# -----------------------------------------------------------------------------
# 1. Read data and EXCLUDE buildings with category == 2
# -----------------------------------------------------------------------------
data_wide <- read_csv(data_path)

# Ensure EGID exists
if (!"EGID" %in% colnames(data_wide)) {
  stop("Column 'EGID' not found. Please provide a building identifier.")
}

# Count unique buildings before any exclusion
total_buildings_before <- n_distinct(data_wide$EGID)

# Drop buildings where category == 2
if ("category" %in% colnames(data_wide)) {
  n_buildings_before <- n_distinct(data_wide$EGID)
  data_wide <- data_wide %>% filter(category != 2)
  n_buildings_after <- n_distinct(data_wide$EGID)
  cat("Excluded", n_buildings_before - n_buildings_after, 
      "unique buildings with category == 2.\n")
} else {
  warning("Column 'category' not found. No exclusion applied.")
}

# -----------------------------------------------------------------------------
# 2. Reshape to long, using EGID as the panel identifier
#    Recode 98/99 to NA to treat them as missing.
#    This will drop the rows with 98/99 and the following year
#    (because the lag becomes unknown), but the building can re-enter
#    in later years if the data becomes valid.
# -----------------------------------------------------------------------------
data_long <- data_wide %>%
  pivot_longer(
    cols = starts_with("Clean - "),
    names_to = "year",
    values_to = "clean_status",
    names_prefix = "Clean - "
  ) %>%
  mutate(year = as.integer(year)) %>%
  # ---- RECODE 98/99 TO NA ----
  mutate(clean_status = if_else(clean_status %in% c(98, 99), NA_real_, clean_status)) %>%
  arrange(EGID, year) %>%
  group_by(EGID) %>%
  mutate(
    clean_lag = lag(clean_status),
    event = if_else(clean_status == 1 & clean_lag == 0, 1, 0),
    at_risk = if_else(clean_lag == 0, 1, 0)
  ) %>%
  ungroup()

# -----------------------------------------------------------------------------
# 3. Create risk set – keep EGID, GDENR, VPI, Vote
# -----------------------------------------------------------------------------
risk_set <- data_long %>%
  filter(at_risk == 1 & !is.na(clean_lag)) %>%
  select(EGID, year, event, 
         GBAUPS, GETYP, GKATS, Type_Ville, Dummy_Subvention,
         GDENR, VPI, Vote)

# -----------------------------------------------------------------------------
# 4. Prepare factors and clean data (drop_na)
# -----------------------------------------------------------------------------
# Count rows and unique buildings before drop_na
rows_before <- nrow(risk_set)
buildings_before <- n_distinct(risk_set$EGID)

clean_data <- risk_set %>%
  select(event, Dummy_Subvention, GBAUPS, GETYP, GKATS, Type_Ville, year,
         EGID, GDENR, VPI, Vote) %>%
  mutate(
    year = as.factor(year),
    GBAUPS = as.factor(GBAUPS),
    GETYP  = as.factor(GETYP),
    GKATS  = as.factor(GKATS),
    Type_Ville = as.factor(Type_Ville),
    Dummy_Subvention = as.factor(Dummy_Subvention)
  ) %>%
  drop_na()

rows_after <- nrow(clean_data)
buildings_after <- n_distinct(clean_data$EGID)

cat("\nRows in risk set before drop_na:", rows_before, "\n")
cat("Rows after drop_na:", rows_after, "\n")
cat("Rows removed due to missing data:", rows_before - rows_after, "\n")
cat("Unique buildings before drop_na:", buildings_before, "\n")
cat("Unique buildings after drop_na:", buildings_after, "\n")
cat("Unique buildings with at least one missing row:", 
    buildings_before - buildings_after, "\n")

# -----------------------------------------------------------------------------
# 5. Set reference levels (dynamic year reference)
# -----------------------------------------------------------------------------
get_smallest_level <- function(x) {
  lvls <- levels(x)
  num_lvls <- as.numeric(as.character(lvls))
  lvls[which.min(num_lvls)]
}

if (is.null(year_ref)) {
  year_ref <- as.character(min(as.numeric(as.character(clean_data$year))))
}

clean_data <- clean_data %>%
  mutate(
    year = fct_relevel(year, year_ref),
    Dummy_Subvention = fct_relevel(Dummy_Subvention, subsidy_ref),
    GBAUPS = fct_relevel(GBAUPS, if (!is.null(gbaups_ref)) gbaups_ref else get_smallest_level(GBAUPS)),
    GETYP = fct_relevel(GETYP, if (!is.null(getyp_ref)) getyp_ref else get_smallest_level(GETYP)),
    GKATS = fct_relevel(GKATS, if (!is.null(gkats_ref)) gkats_ref else get_smallest_level(GKATS)),
    Type_Ville = fct_relevel(Type_Ville, if (!is.null(type_ville_ref)) type_ville_ref else as.character(sort(unique(Type_Ville))[1]))
  )

# -----------------------------------------------------------------------------
# 6. Print reference levels and summary
# -----------------------------------------------------------------------------
cat("\n========================================\n")
cat("Reference Levels for Categorical Variables\n")
cat("========================================\n")
cat("year (baseline)             :", levels(clean_data$year)[1], "\n")
cat("Dummy_Subvention (baseline) :", levels(clean_data$Dummy_Subvention)[1], "\n")
cat("GBAUPS (baseline)           :", levels(clean_data$GBAUPS)[1], "\n")
cat("GETYP (baseline)            :", levels(clean_data$GETYP)[1], "\n")
cat("GKATS (baseline)            :", levels(clean_data$GKATS)[1], "\n")
cat("Type_Ville (baseline)       :", levels(clean_data$Type_Ville)[1], "\n")
cat("Additional numeric covariates: VPI, Vote\n")
cat("========================================\n\n")

cat("Final number of rows (building-year):", nrow(clean_data), "\n")
cat("Final number of unique buildings:", n_distinct(clean_data$EGID), "\n\n")

# -----------------------------------------------------------------------------
# 7. Fit models with REGULAR (non-clustered) standard errors
# -----------------------------------------------------------------------------
# No cluster argument -> standard errors are i.i.d.
model <- feglm(
  event ~ Dummy_Subvention + GBAUPS + GETYP + GKATS + Type_Ville + year + VPI + Vote,
  data = clean_data,
  family = binomial(link = "cloglog")
)

null_model <- feglm(
  event ~ 1,
  data = clean_data,
  family = binomial(link = "cloglog")
)

# -----------------------------------------------------------------------------
# 8. Coefficient table (using coeftable to avoid tidy() error)
# -----------------------------------------------------------------------------
cat("========================================\n")
cat("Coefficient Table (Full Model)\n")
cat("(Regular (non-clustered) Standard Errors)\n")
cat("========================================\n")

# Extract coefficient table from fixest object
coef_table <- coeftable(model)
# Convert to data frame for easier manipulation
coef_df <- data.frame(
  term = rownames(coef_table),
  estimate = coef_table[, "Estimate"],
  std.error = coef_table[, "Std. Error"],
  z.value = coef_table[, "z value"],
  p.value = coef_table[, "Pr(>|z|)"]
)
# Add confidence intervals (Wald)
coef_df <- coef_df %>%
  mutate(
    conf.low = estimate - 1.96 * std.error,
    conf.high = estimate + 1.96 * std.error
  )
# Print without extra arguments that may cause errors
print(coef_df, row.names = FALSE, na.print = "")

# -----------------------------------------------------------------------------
# 9. Hazard Ratios from coefficient table
# -----------------------------------------------------------------------------
hr <- coef_df %>%
  mutate(
    Hazard_Ratio = exp(estimate),
    CI_lower = exp(conf.low),
    CI_upper = exp(conf.high)
  ) %>%
  select(term, Hazard_Ratio, CI_lower, CI_upper, p.value)

cat("\n========================================\n")
cat("Hazard Ratios\n")
cat("========================================\n")
# Simply print the data frame, no 'n = Inf' to avoid errors
print(hr, na.print = "")

# -----------------------------------------------------------------------------
# 10. Goodness-of-Fit
# -----------------------------------------------------------------------------
cat("\n========================================\n")
cat("Goodness-of-Fit Measures\n")
cat("========================================\n")
ll_full <- as.numeric(logLik(model))
ll_null <- as.numeric(logLik(null_model))
cat("Log-likelihood (full):", ll_full, "\n")
cat("Log-likelihood (null):", ll_null, "\n\n")
cat("AIC (full):", AIC(model), "\n")
cat("BIC (full):", BIC(model), "\n")
cat("AIC (null):", AIC(null_model), "\n")
cat("BIC (null):", BIC(null_model), "\n\n")
mf_r2 <- 1 - (ll_full / ll_null)
cat("McFadden R² (manual):", mf_r2, "\n")
k <- length(coef(model))
adj_mf_r2 <- 1 - (ll_full - k) / ll_null
cat("Adjusted McFadden R² (manual):", adj_mf_r2, "\n\n")
lrt_result <- lrtest(null_model, model)
cat("Likelihood-Ratio Test:\n")
print(lrt_result)
