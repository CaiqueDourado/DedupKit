// Groups the listings of a CSV (columns id,name,brand,code,url,image,source; only id and name
// are required) and prints every cluster with the rule that formed it, then the refused pairs.
//   dotnet run --project samples/MatchListings -- ../examples/listings.csv
using System.Text;
using DedupKit;

if (args.Length < 1)
{
    Console.Error.WriteLine("usage: MatchListings <listings.csv>");
    return 1;
}

var rows = ReadCsv(args[0]);
var header = rows[0];
string Col(string[] row, string name)
{
    var i = Array.IndexOf(header, name);
    return i >= 0 && i < row.Length ? row[i] : "";
}

var records = rows.Skip(1).Select(r => new DedupKit.Record(
    Col(r, "id"), Col(r, "name"), Col(r, "brand"),
    Col(r, "code").Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries),
    Col(r, "url"), Col(r, "image"), Col(r, "source"))).ToList();
var byId = records.ToDictionary(r => r.Id);

var result = Matcher.Match(records);
foreach (var cluster in result.Clusters)
{
    Console.WriteLine($"cluster {result.ClusterOf[cluster[0]]}");
    foreach (var id in cluster)
    {
        var how = result.Via.TryGetValue(id, out var v) ? $"  <- {v.Rule}: {v.Value}" : "";
        Console.WriteLine($"  {id,-6} {byId[id].Name}{how}");
    }
}
Console.WriteLine();
foreach (var r in result.Rejected)
    Console.WriteLine($"refused {r.A} x {r.B} ({r.Rule}): {r.Reason}");
return 0;

static List<string[]> ReadCsv(string path)
{
    // Minimal RFC 4180 reader: quoted fields, doubled quotes, commas and line breaks inside quotes.
    var rows = new List<string[]>();
    var row = new List<string>();
    var field = new StringBuilder();
    var text = File.ReadAllText(path, Encoding.UTF8);
    bool quoted = false;
    for (int i = 0; i < text.Length; i++)
    {
        char c = text[i];
        if (quoted)
        {
            if (c == '"' && i + 1 < text.Length && text[i + 1] == '"') { field.Append('"'); i++; }
            else if (c == '"') quoted = false;
            else field.Append(c);
        }
        else if (c == '"') quoted = true;
        else if (c == ',') { row.Add(field.ToString()); field.Clear(); }
        else if (c == '\n' || c == '\r')
        {
            if (c == '\r' && i + 1 < text.Length && text[i + 1] == '\n') i++;
            row.Add(field.ToString()); field.Clear();
            if (row.Count > 1 || row[0].Length > 0) rows.Add(row.ToArray());
            row.Clear();
        }
        else field.Append(c);
    }
    if (field.Length > 0 || row.Count > 0) { row.Add(field.ToString()); rows.Add(row.ToArray()); }
    return rows;
}
