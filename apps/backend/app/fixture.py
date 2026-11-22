"""Deliberately synthetic evidence, never presented as real research."""
EVIDENCE = [
    {'id': 'ev_01', 'source_id': 'src_01', 'title': 'Interview A · independent designer', 'location': 'Lines 8–9', 'kind': 'Synthetic interview', 'excerpt': 'I keep a separate sheet for invoices. Every Friday I check which ones are still unpaid and write another follow-up email.', 'limitation': 'Invented participant and quotation for interface testing.'},
    {'id': 'ev_02', 'source_id': 'src_02', 'title': 'Interview B · freelance developer', 'location': 'Lines 12–13', 'kind': 'Synthetic interview', 'excerpt': 'The hard part is knowing whether the client saw my reminder. I copy invoice details into the email each time.', 'limitation': 'Invented participant and quotation for interface testing.'},
    {'id': 'ev_03', 'source_id': 'src_03', 'title': 'Alternative review · spreadsheet workflow', 'location': 'Observation 2', 'kind': 'Synthetic workflow note', 'excerpt': 'The example spreadsheet tracks amount, due date and payment status. Reminder messages are drafted in a separate email tool.', 'limitation': 'Illustrative workflow, not an assessment of a commercial product.'}
]

def research_brief(project):
    return {
        'id': f'fixture-{project.id}', 'project_id': project.id,
        'title': 'Making invoice follow-up less manual',
        'subtitle': 'An example of how evidence becomes a testable product direction.',
        'mode': 'fixture', 'version': 1,
        'notice': 'Sample brief · All interviews, quotations and findings below are synthetic. No live research or AI generation has run. Your project question is saved separately.',
        'sections': [
            {'id': 'summary', 'title': 'Executive summary', 'eyebrow': '01 / THE TAKEAWAY', 'blocks': [
                {'id': 'c1', 'type': 'observation', 'text': 'In this sample, invoice tracking and payment reminders happen across separate tools.', 'evidence_ids': ['ev_01', 'ev_03']},
                {'id': 'c2', 'type': 'inference', 'text': 'A useful starting point may be reducing the effort of following up, rather than replacing the entire invoicing workflow.', 'evidence_ids': ['ev_01', 'ev_02'], 'limitation': 'A directional interpretation of two invented interviews; not evidence of market demand.'}
            ]},
            {'id': 'problems', 'title': 'Customer problems', 'eyebrow': '02 / WHAT WE OBSERVED', 'blocks': [
                {'id': 'c3', 'type': 'observation', 'text': 'Participant A describes a recurring manual check for unpaid invoices.', 'evidence_ids': ['ev_01']},
                {'id': 'c4', 'type': 'observation', 'text': 'Participant B describes copying invoice details and uncertainty about reminder visibility.', 'evidence_ids': ['ev_02']}
            ]},
            {'id': 'alternatives', 'title': 'Existing alternatives', 'eyebrow': '03 / THE CURRENT WORKAROUND', 'blocks': [
                {'id': 'c5', 'type': 'observation', 'text': 'The illustrative spreadsheet records payment status, while reminders are handled separately in email.', 'evidence_ids': ['ev_03']}
            ]},
            {'id': 'opportunity', 'title': 'Opportunity to explore', 'eyebrow': '04 / A PRODUCT HYPOTHESIS', 'blocks': [
                {'id': 'c6', 'type': 'hypothesis', 'text': 'For freelancers who already track invoices, a reviewable reminder draft could reduce repetitive work while preserving control over client communication.', 'evidence_ids': ['ev_01', 'ev_02', 'ev_03'], 'limitation': 'Untested. Validate usefulness, trust and willingness to adopt before building automation.'}
            ]},
            {'id': 'validation', 'title': 'What to validate next', 'eyebrow': '05 / THE NEXT DECISION', 'blocks': [
                {'id': 'c7', 'type': 'experiment', 'text': 'Run five exploratory interviews with freelancers who invoice clients. Ask them to show their last follow-up workflow, then test a clickable reminder-draft prototype.', 'evidence_ids': [], 'limitation': 'Proposed experiment, not a completed study.'},
                {'id': 'c8', 'type': 'experiment', 'text': 'Use a provisional decision rule: at least three participants complete the draft-review task without help and describe a recent instance when it would have been useful. This is a discovery signal, not statistical validation.', 'evidence_ids': [], 'limitation': 'Researcher-proposed threshold; revise after observing the sessions.'}
            ]}
        ],
        'limitations': ['All evidence is synthetic and exists only to demonstrate the product.', 'No real competitor comparison, prevalence estimate or market-size claim is included.', 'This invoice example is fixed; it does not answer arbitrary project questions.'],
        'evidence': EVIDENCE
    }
