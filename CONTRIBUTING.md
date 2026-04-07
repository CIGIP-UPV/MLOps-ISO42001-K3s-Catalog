# Contributing to the K3S ISO/IEC 42001 Solution Catalog

Thank you for contributing to this catalog. Follow these guidelines to add new solutions or improve existing ones.

---

## Adding a New Solution

1. **Choose the correct location**: `catalog/<tier>/<category>/<solution-name>/`
   - Tier: `edge` / `platform` / `enterprise`
   - Category: `data-ingestion` / `ai-inference` / `monitoring` / `security` / `storage` / `ai-lifecycle` / `access-management` / `helpdesk` / `dashboards` / `orchestration`

2. **Copy the solution template**:
   ```bash
   cp -r templates/solution-template/ catalog/<tier>/<category>/<solution-name>/
   ```

3. **Fill in the README.md** following the template structure:
   - Complete the metadata table (Tier, Category, RA Component, ISO clauses, Helm chart)
   - Write a clear description of the solution's role in the reference architecture
   - Complete the ISO/IEC 42001 mapping table
   - List prerequisites
   - Provide installation commands

4. **Fill in the questionnaire.md**: Every solution must have a questionnaire that guides configuration decisions. Questions should map directly to `values.yaml` parameters.

5. **Add a `manifests/` directory**: Provide at minimum a `values.yaml` reference file. Add K3S-specific manifests (Deployments, Services, ConfigMaps) if no Helm chart is available.

6. **Update the catalog index**: Add the new solution to `catalog/README.md` in both the matrix table and the tier-specific list.

7. **Update the compliance matrix**: If the solution addresses any ISO/IEC 42001 Annex B requirements, add or update the relevant rows in `compliance/iso42001-mapping.md`.

---

## Solution Quality Checklist

Before submitting a new solution entry, verify:

- [ ] README metadata table is complete
- [ ] ISO/IEC 42001 mapping is accurate and references specific clause numbers
- [ ] Prerequisites are listed completely (including K3S version, storage class, network requirements)
- [ ] Installation commands are tested on K3S
- [ ] Questionnaire has at least 3 sections (functional, security/compliance, resources)
- [ ] `values.yaml` is annotated with comments linking to questionnaire answers
- [ ] Related Solutions section links to at least one other catalog entry
- [ ] Catalog index (`catalog/README.md`) updated
- [ ] Compliance matrix (`compliance/iso42001-mapping.md`) updated if relevant

---

## Updating Existing Solutions

When updating a solution (e.g., new Helm chart version, additional ISO mapping):

1. Update the relevant README and questionnaire files.
2. Test the new installation commands on a K3S cluster.
3. Update the compliance matrix if the ISO coverage has changed.
4. Note the change in a `CHANGELOG.md` within the solution directory (create if absent).

---

## Style Guidelines

- Use present tense in descriptions ("Falco **detects** anomalous activity...")
- Reference ISO/IEC 42001 clauses with full identifiers (e.g., B.6.2.6.7, not just "clause 6.2.6.7")
- Link to related solutions using relative paths
- Use tables for structured information (configuration options, ISO mappings)
- Keep questionnaire answers actionable — each answer should lead to a specific configuration decision
