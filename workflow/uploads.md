# Uploads

Uploads of completed analyses results that are stored in _Housekeeper_ happen automatically.

    :stopwatch: rasta:~/servers/crontab/upload-auto.sh
    :man_technologist: cg upload auto
    :man_technologist: cg upload -f FAMILY-ID

This process is split into multiple steps:

## Coverage

Coverage and completeness levels calculated by _Sambamba_ are uploaded to _Chanjo_. Only one set of results are stored for each sample so old results will automatically replace previous ones.

Coverage/completeness is stored on transcript level for all RefSeq transcripts (+ MT all transcripts) as defined in _Scout_.

    :man_technologist: cg upload coverage FAMILY-ID

## Scout

We deliver variants along with annotations to _Scout_ - the main portal for data delivery.
