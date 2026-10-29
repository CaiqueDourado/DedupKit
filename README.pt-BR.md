# DedupKit

[English](README.md)

[![Python](https://github.com/CaiqueDourado/DedupKit/actions/workflows/python.yml/badge.svg)](https://github.com/CaiqueDourado/DedupKit/actions/workflows/python.yml)
[![.NET](https://github.com/CaiqueDourado/DedupKit/actions/workflows/dotnet.yml/badge.svg)](https://github.com/CaiqueDourado/DedupKit/actions/workflows/dotnet.yml)
![Licença: MIT](https://img.shields.io/badge/license-MIT-blue)

![DedupKit](docs/img/cover.pt-BR.png)

Encontra anúncios que são o mesmo produto em dados em português do Brasil, e recusa os que
só parecem iguais.

```text
Fone de Ouvido sem Fio JBL Tune 510BT Preto     ┐
FONES DE OUVIDO JBL TUNE 510BT S/ FIO PRETO     ├─ mesmo produto
Fone Ouvido JBL Tune 510BT Bluetooth Preto      ┘

Chuveiro Elétrico Lorenzetti Acqua Duo 220V 7800W  ┐ mesmo EAN, recusado:
Chuveiro Eletrico Lorenzetti Acqua Duo 127V 5500W  ┘ power_w: 7800 vs 5500
```

O DedupKit é a lógica de agrupamento de um catálogo comparador de preços (2019–2022), reescrita
como biblioteca, testada e medida. Roda em **Python e .NET com resultados idênticos**: as duas
versões são conferidas contra os mesmos 448 textos e 8 configurações de agrupamento em
[`testdata/golden.json`](testdata/golden.json). Nenhuma dependência nas duas linguagens.

- **Chaves de texto para português:** remoção de acentos, fingerprints no estilo OpenRefine e
  n-gramas de caracteres, redução de plural (`fogões` → `fogao`, `jardins` → `jardim`), chave
  fonética (`xuveiro` = `chuveiro`, `caçarola` = `cassarola`) e URLs sem parâmetros de rastreamento.
- **Códigos como as lojas preenchem:** dígito verificador do GTIN, valores de enchimento
  (`SEM GTIN`, `0`, `7.89E+12`), códigos longos e curtos e uma lista de códigos que uma loja usa para tudo.
- **Conferência de atributos:** dois anúncios nunca são juntados quando os nomes dizem medidas
  (`400g` vs `500g`, `110V` vs `220V`, `20x30` vs `30x40`), memórias, cores, gênero, tamanhos de roupa ou
  calçado (`- 38 -` vs `- 40 -`) ou quantidades (`Kit 3 Pares` vs `Kit 6 Pares`) diferentes. Ela sabe que
  110 V e 127 V são a mesma rede elétrica e que inox, prata e cromado são a mesma cor.
- **Trilha de auditoria:** cada ligação registra a regra e o valor que a criaram, e cada par recusado diz o motivo.

## Instalação

```bash
pip install "dedupkit-br @ git+https://github.com/CaiqueDourado/DedupKit#subdirectory=python"
```

```bash
dotnet add package DedupKit   # depois de publicado; até lá, referencie dotnet/src/DedupKit
```

## Uso

Python:

```python
from dedupkit_br import Record, match

records = [
    Record("1", "Fone de Ouvido sem Fio JBL Tune 510BT Preto", brand="JBL", codes=("6925281979309",)),
    Record("2", "FONES DE OUVIDO JBL TUNE 510BT S/ FIO PRETO", brand="JBL"),
    Record("5", "Chuveiro Elétrico Lorenzetti Acqua Duo 220V 7800W", codes=("7891129220911",)),
    Record("6", "Chuveiro Eletrico Lorenzetti Acqua Duo 127V 5500W", codes=("7891129220911",)),
]
result = match(records)
result.clusters      # [['1', '2']]
result.via["2"]      # ('name_tokens', '510bt fio fone jbl ouvido preto tune')
result.rejected[0]   # Rejected(a='5', b='6', rule='code', value='7891129220911', reason='power_w: 7800 vs 5500')
```

C#:

```csharp
using DedupKit;

var result = Matcher.Match(records);                       // mesmos grupos, ligações e recusas
var estrito = Matcher.Match(records, new MatchOptions { Rules = Rules.ByName("code", "name", "name_tokens", "url", "short_code_brand") });
```

Linha de comando, sobre um CSV com cabeçalho:

```bash
dedupkit-br match examples/listings.csv --brand brand --code code --url url --source source --rejected recusados.csv > grupos.csv
```

O exemplo em .NET faz o mesmo: `dotnet run --project dotnet/samples/MatchListings -- examples/listings.csv`.

As peças também são públicas:

| Python | C# | Exemplo |
|---|---|---|
| `normalize` | `TextKeys.Normalize` | `"Pendente TLF-28, Preto!"` → `"pendente tlf 28 preto"` |
| `fingerprint` | `TextKeys.Fingerprint` | `"Preto Pendente preto"` → `"pendente preto"` |
| `token_key` | `TextKeys.TokenKey` | `"Fones de Ouvido s/ Fio"` → `"fio fone ouvido"` |
| `phonetic_key` | `TextKeys.PhoneticKey` | `"Xuveiro"` e `"Chuveiro"` → `"XVR"` |
| `normalize_url` | `TextKeys.NormalizeUrl` | `"https://www.Loja.com.br/p/12/?utm_source=x&id=3"` → `"loja.com.br/p/12?id=3"` |
| `attributes` | `ProductAttributes.Extract` | `"Ração 2,5kg"` → `{weight_kg: {2.5}}` |
| `conflict` | `ProductAttributes.Conflict` | `"110V"`, `"220V"` → `"voltage_v: 110 vs 220"` |
| `is_valid_gtin`, `code_class` | `Codes.IsValidGtin`, `Codes.Classify` | `"7891234567895"` → válido, `long` |

## Como fica uma decisão

Os anúncios 5 e 6 de [`examples/listings.csv`](examples/listings.csv) têm o mesmo código de barras, então a regra
`code` os coloca no mesmo bloco; a conferência de atributos encontra potência e voltagem diferentes, e o par é
recusado com o motivo.

![Uma decisão em JSON](docs/img/decision-json.png)

JSON completo: [`docs/example-decision.json`](docs/example-decision.json), gerado por
[`scripts/make_json.py`](scripts/make_json.py) a partir do que `match()`, `attributes()` e `conflict()` devolvem.

## Como funciona

```mermaid
flowchart TD
    A[Anúncios: nome, marca, códigos, URL, imagem] --> B[Chaves por regra<br/>EAN, nome, fingerprint, fonética,<br/>n-gramas, palavras, URL, código curto + marca, imagem]
    B --> C{Mesmo valor de chave?}
    C -- bloco com mais de 100 --> S[Ignorado e informado]
    C -- sim --> D{Casou por EAN e<br/>nenhuma palavra em comum?}
    D -- sim --> R[Recusado, com o motivo]
    D -- não --> E{Tamanho, voltagem, cor,<br/>memória... diferentes?}
    E -- sim --> R
    E -- não --> L[Ligação: regra + valor]
    L --> F[Grupos: componentes conectados<br/>ou o modo de dois saltos de 2019]
```

As regras exatas, para as duas linguagens, estão em [spec/ALGORITHMS.md](spec/ALGORITHMS.md) (em inglês).

### Um nome passando por cada chave

Cada regra de nome transforma o nome numa chave; anúncios com a mesma chave caem no mesmo bloco. Duas formas reais
de escrever o mesmo fone, e o que cada chave faz com elas (o nome da regra, com a trava que deixa de fora chaves
curtas ou vazias):

```mermaid
flowchart LR
  A["A: Fone de Ouvido sem Fio JBL Tune 510BT Preto<br/>B: FONES DE OUVIDO JBL TUNE 510BT S/ FIO PRETO"]
  A --> N["normalize · regra name (2+ palavras)<br/>A: fone de ouvido sem fio jbl tune 510bt preto<br/>B: fones de ouvido jbl tune 510bt s fio preto"] --> N2["✗ diferentes"]
  A --> F["fingerprint · regra name_fingerprint (3+ palavras distintas)<br/>palavras únicas, ordenadas<br/>A: 510bt de fio fone jbl ouvido preto sem tune<br/>B: 510bt de fio fones jbl ouvido preto s tune"] --> F2["✗ fone ≠ fones, sem ≠ s"]
  A --> P["phonetic_key · regra name_phonetic<br/>sons por palavra, na ordem<br/>A: FN D OVD SM F JB TN 510BT PRT<br/>B: FNS D OVD JB TN 510BT S F PRT"] --> P2["✗ ordem das palavras difere"]
  A --> G["ngram_fingerprint · regra name_ngram (10+ letras)<br/>bigramas de caracteres, únicos, ordenados"] --> G2["✗ diferentes"]
  A --> T["token_key · regra name_tokens (2+ palavras)<br/>sem stopwords (de, sem, s), no singular, ordenadas<br/>A e B: 510bt fio fone jbl ouvido preto tune"] --> T2["✓ mesmo bloco"]
```

As outras regras usam o código de barras (GTIN longo, e código curto + marca), a URL sem parâmetros de rastreio e a
assinatura da imagem. Uma chave com mais de 100 anúncios (`max_block`) é ignorada e informada: é um código genérico,
não um produto.

### Conferindo um par

Dois anúncios no mesmo bloco são só candidatos. Isto é o que decide:

```mermaid
flowchart TD
  P["par no mesmo bloco<br/>(qualquer regra)"] --> L{"já ligados<br/>por outra regra?"}
  L -- sim --> SKIP["nada a fazer"]
  L -- não --> C{"regra = código<br/>de barras?"}
  C -- sim --> W{"os nomes têm<br/>palavra em comum?"}
  W -- não --> R1["recusado: nenhuma palavra em comum<br/>(a loja reusou o código)"]
  W -- sim --> X
  C -- não --> X["extrai os atributos de cada nome<br/>peso, volume, voltagem, potência, memória, bateria,<br/>comprimento, tela, BTU, cor, gênero, tamanho,<br/>quantidade do kit, listas de dimensões"]
  X --> D{"para cada atributo<br/>que os dois informam"}
  D -- "listas de dimensões" --> DL{"uma lista começa<br/>com a outra?<br/>(20x30 e 20x30x10)"}
  DL -- não --> R2["recusado: dimensões 20x30 vs 30x40"]
  D -- "outros atributos" --> V{"algum valor<br/>em comum?<br/>(110 = 127 V,<br/>inox = prata = cromado)"}
  V -- não --> R3["recusado: power_w 7800 vs 5500<br/>size 38 vs 40 · quantity 3 vs 6"]
  DL -- sim --> OK
  V -- sim --> OK{"conferência de marca ligada?<br/>(desligada por padrão)"}
  OK -- "sim, marcas diferentes" --> R4["recusado: marca"]
  OK -- "não / mesma marca" --> LINK["liga, com regra e valor da chave"]
  LINK --> CL["grupos: componentes conexos<br/>(ou o modo de 2 saltos de 2019)"]
```

Toda recusa volta com a regra, o valor da chave e o motivo, então um erro pode ser rastreado até a linha que o causou.

## O que cada proteção rende

Medido em 4.073 anúncios sintéticos de 1.138 variantes de produto com resposta conhecida
([`tools/synth_listings.py`](tools/synth_listings.py)). Eles imitam o que tornava o catálogo real difícil:
cada loja escrevendo o nome do seu jeito, tamanhos e cores de um produto dividindo o mesmo EAN ou a mesma foto,
SKUs reaproveitados, a imagem "sem foto", a mesma página coletada duas vezes.

![Precisão e cobertura de cada configuração](docs/img/safeguards.pt-BR.png)

| Configuração | Precisão | Cobertura |
|---|---:|---:|
| O catálogo de 2019: todas as chaves, dois saltos, bug do fingerprint | 23,4% | 91,2% |
| Fingerprint corrigido, EAN sem conferir palavras | 25,9% | 91,2% |
| + conferência de palavras no EAN | 44,4% | 91,2% |
| + conferência de atributos (padrão) | 81,5% | 90,2% |
| + conferência de marca | 87,6% | 90,2% |
| Chaves recomendadas + atributos | 89,9% | 85,1% |

Dos 1.274 pares recusados, 6 eram de fato o mesmo produto. Velocidade: cerca de 41 mil anúncios em 13 segundos em Python.
Os números por regra estão em [evaluation/results.md](evaluation/results.md); `python evaluation/evaluate.py` os reproduz.

Dados sintéticos dão respostas exatas, mas favorecem qualquer método feito para eles. Por isso os padrões também
foram conferidos numa amostra real (próxima seção), e uma proteção que parecia boa aqui, a de marca, vem
desligada porque os dados reais a derrubaram.

## Em dados reais

[`evaluation/real_sample.py`](evaluation/real_sample.py) roda a conferência de atributos sobre as 28.569 ofertas
da [amostra pública do catálogo](https://github.com/CaiqueDourado/brazilian-ecommerce-products),
agrupadas em 2019 em 4.030 grupos. Sem mudar nenhum parâmetro, **795 desses grupos seriam divididos**.
Pares recusados, por motivo: tamanho de roupa ou calçado 2.792, cor 721, comprimento 330, lista de dimensões 323,
quantidade 267, volume 113, voltagem 93, tela 43, memória 31, peso 25, potência 9, e 41 casamentos por EAN cujos
nomes não têm nenhuma palavra em comum. A maior parte das recusas por tamanho é o mesmo calçado ou roupa em outro
tamanho, que o catálogo de 2019 deixava numa página só; o DedupKit trata cada tamanho como um produto, como faz o EAN.

| Regra | Anúncio A | Anúncio B | Motivo da recusa |
|---|---|---|---|
| code | Mass Way 2500 Baunilha 400g | Mass Way 2500 (500g) - Baunilha | peso 0,4 vs 0,5 kg |
| code | Squeeze Alumínio 500ml - Preto - Acte Sports | Squeeze Alumínio 750Ml - Preto - Acte Sports | volume 0,5 vs 0,75 l |
| code | Sutiã de Amamentação Preto Medela | Sutiã de Amamentação Branco Medela | cor |
| image | Toalheiro Elétrico A20 220v Emmeti | Toalheiro Elétrico A10 127v Emmeti | voltagem 220 vs 127 |
| image | Pen Drive 32gb de Couro Branco com Argola ... | Pen Drive 4gb Personalizado de Couro Branco ... | memória 32 vs 4 GB |

No catálogo antigo, cada um desses pares era uma única página de produto. O catálogo completo (114,6 milhões de ofertas, 18,3 milhões de grupos) está no [Kaggle](https://www.kaggle.com/datasets/caiquedourado/catalogo-produtos-ecommerce-brasil), para rodar o DedupKit em escala. Já a conferência de marca recusou
6.729 pares na mesma amostra, a maioria corretos, porque os marketplaces preenchem o campo marca com o nome
do vendedor. Ligue (`check_brands=True`) só quando o seu campo de marca for limpo.

### Conferido par a par

O [dataset de pares para matching](https://github.com/CaiqueDourado/product-matching-pairs-portuguese) tem 780 pares candidatos do catálogo conferidos um a um, no nível de SKU.
Juntar todo candidato, como fazia o catálogo de 2019, dá 25% de precisão; as conferências de palavra e atributos do
DedupKit dão **47% de precisão com 91% de cobertura**; somando uma conferência de número de modelo (TB125 × TB112,
PS3 × PS4), 83% com 68%. As regras de atributos da 0.2.0 (tamanhos, quantidades, listas de dimensões, 110 = 127 V)
foram escritas a partir dos erros encontrados nesses pares.

## Por que estas chaves

Em 2019, antes de escrever a rotina de agrupamento, o autor calculou cerca de 15 chaves para cada nome de produto
distinto do catálogo (cinco variantes de Soundex, três de Metaphone, o fingerprint e o n-grama do OpenRefine, três
fingerprints de palavras, uma normalização "soft", um hash e as chaves omission e skeleton de correção ortográfica),
comparou-as par a par ("igual em A, diferente em B") e anotou as decisões no SQL: usar o fingerprint de palavras sem
stopwords e descartar a variante que também separava e ordenava palavras ("muitos falsos positivos"). As chaves do
DedupKit são as que sobraram. O [`evaluation/keys_benchmark.py`](evaluation/keys_benchmark.py) mede de novo essas
chaves, e as descartadas que dá para reconstruir, nos 715 pares decididos do conjunto gold e nos 9.971 nomes
distintos da amostra do catálogo:

| Chave | No DedupKit | Pares do mesmo produto unidos | Pares de produtos diferentes unidos | Precisão | Blocos | Maior bloco |
|---|:---:|---:|---:|---:|---:|---:|
| `normalize` | sim | 11 (7%) | 0 | 100% | 8.855 | 7 |
| `fingerprint` | sim | 16 (10%) | 1 | 94% | 8.448 | 20 |
| `token_key` | sim | 16 (10%) | 1 | 94% | 8.319 | 22 |
| `phonetic_key` | sim | 12 (7%) | 2 | 86% | 8.776 | 10 |
| `ngram_fingerprint` | sim | 13 (8%) | 0 | 100% | 8.759 | 8 |
| `fingerprint_2019` | não | 19 (12%) | 31 | 38% | 7.766 | 23 |
| `phonetic_no_digits` | não | 22 (13%) | 219 | 9% | 7.522 | 22 |
| `skeleton` | não | 36 (22%) | 254 | 12% | 6.726 | 36 |
| `skeleton_2019` | não | 23 (14%) | 219 | 10% | 7.474 | 21 |
| `omission` | não | 45 (27%) | 268 | 14% | 6.337 | 43 |

- **Uma chave de nome sozinha acha poucos destes pares**, e é o esperado: os pares gold foram escolhidos difíceis
  (mesmo código de barras ou foto, nome escrito de outro jeito). Chaves de nome fazem blocos; o código, a foto e a
  conferência de atributos fazem o resto.
- **Números fazem parte do produto.** A chave fonética sem números junta 219 produtos diferentes (*Shampoo Aussie
  Moist 865ML* × *180 Ml*) para achar 22 certos.
- **Chaves de correção ortográfica ignoram palavras.** Omission e skeleton (Pollock e Zamora, via Talisman) guardam
  cada letra uma vez, e nomes sem relação colidem: a omission pôs *Acabamento para Registro Gaveta… Deca* e *Bandagem
  Vollke Elastica Preta 5 Metros* na mesma chave. A versão de 2019 do skeleton ainda tinha um bug (a parte das vogais
  repetia as consoantes): *DVD Canta Rio 98* e *Dvd - Centurião* viravam `D/VCNTR/VCNTR`.
- **O fingerprint que pulava uma palavra sim, outra não**, de 2019, junta 31 pares de produtos diferentes; o
  corrigido junta 1.
- Não reconstruídos: as variantes de Soundex (um fonetizador de português de 1.100 linhas) e o hash; o `phonetic_key`
  substitui as variantes de Metaphone.

Esses contraexemplos viraram testes nas duas linguagens, com dois limites conhecidos: *Hambúrguer* × *Hamburger* têm
chaves fonéticas diferentes (g × j antes de e), e texto com codificação quebrada (*lav¨¢vel*) precisa ser reparado
antes ([PtBr.Text](https://github.com/CaiqueDourado/PtBr.Text) faz isso).

## A história

O catálogo juntava ofertas de dezenas de lojas com uma rotina em SQL Server (2020–2022) sobre doze
chaves. Ela está publicada, só para leitura, no repositório do catálogo:
[legacy/agrupa_insere_grupos_produtos_similares.sql](https://github.com/CaiqueDourado/brazilian-ecommerce-products/tree/main/legacy).
Reescrevê-la mostrou o que os números acima medem:

- o fingerprint do nome era calculado por uma função que **mantinha uma palavra sim, outra não**, então
  produtos diferentes podiam ter a mesma chave (`legacy_fingerprint` reproduz isso). A mesma função gerou o
  `key_fingerprint` da [base de nomes e sobrenomes](https://github.com/CaiqueDourado/brazilian-names-surnames), onde o bug também está documentado,
  e agrupou as cláusulas dos reviews em 2020, juntando "ótima qualidade" com "péssima qualidade"
  (a [pros-e-contras-ptbr](https://github.com/CaiqueDourado/pros-e-contras-ptbr) agora agrupa com chaves que respeitam a negação);
- casamentos por EAN só conferiam palavra em comum para EANs longos, e nada comparava tamanho ou voltagem,
  então vendedores que usam um EAN para a linha inteira juntavam tudo numa página só;
- o agrupamento em dois saltos dependia da ordem em que as ofertas chegavam (`mode="two_hop"` reproduz;
  o modo padrão `connected` não depende da ordem).

As chaves de imagem vêm da assinatura 16×16 do mesmo catálogo, hoje
[SimilarImageFinder](https://github.com/CaiqueDourado/SimilarImageFinder). Passe qualquer hash de imagem em `image`.

## Limites

- Feito para nomes de produto em português do Brasil. As chaves de texto funcionam em outros textos em alfabeto
  latino, mas stopwords, plurais, regras fonéticas, cores e unidades são do português.
- Baseado em regras e explicável, não aprendido. Não vai saber que "Galaxy S23" e "SM-S911B" são o mesmo celular.
- Todos os pares de um bloco são comparados, então um bloco tem no máximo 100 registros (`max_block`) e é informado quando ignorado.
- A conferência de atributos só vê o que o nome diz. Um anúncio que omite o tamanho casa com os dois tamanhos.

## Relacionados

- [search-pattern-miner](https://github.com/CaiqueDourado/search-pattern-miner): transforma buscas em padrões com os mesmos radicais e chaves, do mesmo autor.
- [google-keywords-dataset](https://github.com/CaiqueDourado/google-keywords-dataset): 38 milhões de buscas do Google agrupadas em padrões com radicais e troca de entidades, a mesma família de chaves usada aqui ([Kaggle](https://www.kaggle.com/datasets/caiquedourado/google-keywords-dataset)).
- [brazilian-ecommerce-products](https://github.com/CaiqueDourado/brazilian-ecommerce-products): as 114,6 milhões de ofertas que este agrupamento juntou.
- [product-matching-pairs-portuguese](https://github.com/CaiqueDourado/product-matching-pairs-portuguese): pares rotulados para medir um matcher, com negativos difíceis.
- [fipe-ficha-tecnica-veiculos](https://github.com/CaiqueDourado/fipe-ficha-tecnica-veiculos): 25,5 milhões de pares veículo × produto casados só pelo nome, a maioria errada. Mostra por que a conferência de atributos e a trilha de auditoria existem.
- [dicionario-portugues](https://github.com/CaiqueDourado/dicionario-portugues): 272 mil palavras do português com chaves fonéticas, rimas e textos gerados por IA ([Kaggle](https://www.kaggle.com/datasets/caiquedourado/dicionario-portugues)): chaves Metaphone, fingerprint e n-gramas para cada palavra.

## Repositório

| Caminho | Conteúdo |
|---|---|
| `python/` | o pacote `dedupkit-br` (`import dedupkit_br`) e seus testes |
| `dotnet/` | a biblioteca `DedupKit`, testes e um exemplo |
| `spec/ALGORITHMS.md` | as regras que as duas versões seguem |
| `testdata/golden.json` | saídas esperadas, geradas por `tools/make_testdata.py` |
| `tools/` | gerador da tabela de acentos, anúncios sintéticos, gerador dos dados de teste |
| `evaluation/` | benchmark sintético, conferência na amostra real, benchmark de chaves (`keys_benchmark.py`), figura |
| `examples/listings.csv` | o exemplo acima |

Créditos das ideias usadas em [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
Contribuições: [CONTRIBUTING.md](CONTRIBUTING.md). Licença MIT.
