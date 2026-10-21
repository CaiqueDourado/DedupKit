import csv

from dedupkit_br import cli


def test_cli(tmp_path, capsys):
    src = tmp_path / "in.csv"
    with open(src, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sku", "titulo", "ean"])
        w.writerow(["1", "Fones de Ouvido JBL sem Fio", "7891234567895"])
        w.writerow(["2", "FONE OUVIDO JBL SEM FIO", ""])
        w.writerow(["3", "Ração Golden 15kg", "7894904567891"])
        w.writerow(["4", "Ração Golden 2,5kg", "7894904567891"])
    rejected = tmp_path / "rejected.csv"
    assert cli.main(["match", str(src), "--id", "sku", "--name", "titulo", "--code", "ean", "--rejected", str(rejected)]) == 0
    rows = list(csv.DictReader(capsys.readouterr().out.splitlines()))
    cluster = {r["id"]: r["cluster"] for r in rows}
    assert cluster["1"] == cluster["2"] and cluster["3"] != cluster["4"]
    assert "weight_kg" in rejected.read_text(encoding="utf-8")
