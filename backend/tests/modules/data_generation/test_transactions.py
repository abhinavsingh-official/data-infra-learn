from app.modules.data_generation.transactions import generate_transaction_batches


def test_rrn_is_unique_across_batches():
    account_ids = [1, 2, 3]
    rrns = []
    for batch in generate_transaction_batches(account_ids, total_count=5_000, batch_size=1_000):
        rrns.extend(row["retrieval_reference_number"] for row in batch)
    assert len(rrns) == len(set(rrns))


def test_recurring_type_and_channel_always_paired():
    """Caught by hand during Module 2's build - transaction_type and
    channel were sampled independently, producing nonsense like a
    'recurring' type on a 'POS' channel."""
    account_ids = [1]
    for batch in generate_transaction_batches(account_ids, total_count=2_000, batch_size=2_000):
        for row in batch:
            is_recurring_type = row["transaction_type"] == "recurring"
            is_recurring_channel = row["channel"] == "recurring"
            assert is_recurring_type == is_recurring_channel


def test_batch_generator_yields_exact_total_count():
    account_ids = [1]
    total = sum(len(batch) for batch in generate_transaction_batches(account_ids, total_count=3_333, batch_size=1_000))
    assert total == 3_333
