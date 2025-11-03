# Rapport d'analyse - Benchmark RAG

## 📊 Statistiques générales

| Métrique | Valeur |
|----------|--------|
| Total de requêtes | 1196 |
| Temps moyen | 40.665s |
| Temps médian | 10.095s |
| Écart-type | 62.234s |
| Min | 0.036s |
| Max | 409.905s |

## 📚 Répartition par corpus

| Corpus | Requêtes | Temps moyen |
|--------|----------|-------------|
| faq | 600 | 29.741s |
| pls | 120 | 0.554s |
| pour_la_science | 476 | 64.547s |

## 🔍 Répartition par mode de recherche

| Mode | Requêtes | Temps moyen |
|------|----------|-------------|
| hybrid | 296 | 55.582s |
| keyword | 300 | 10.630s |
| neural | 300 | 46.757s |
| semantic | 300 | 49.891s |

## 🤖 Répartition par modèle LLM

| Modèle | Requêtes | Temps moyen |
|--------|----------|-------------|
| gpt-oss:20b | 480 | 92.668s |
| llama3.2 | 476 | 8.450s |

## ⚡ Top 5 configurations les plus rapides

| Corpus | Mode | LLM | Multi-query | Temps | N |
|--------|------|-----|-------------|-------|---|
| faq | keyword | nan | nan | 0.056s | 30 |
| pls | neural | nan | nan | 0.063s | 30 |
| faq | neural | nan | nan | 0.066s | 30 |
| faq | hybrid | nan | nan | 0.074s | 30 |
| pls | keyword | nan | nan | 0.149s | 30 |

## 🐌 Top 5 configurations les plus lentes

| Corpus | Mode | LLM | Multi-query | Temps | N |
|--------|------|-----|-------------|-------|---|
| pour_la_science | hybrid | gpt-oss:20b | 1.0 | 181.444s | 30 |
| pour_la_science | semantic | gpt-oss:20b | 1.0 | 172.283s | 30 |
| pour_la_science | neural | gpt-oss:20b | 1.0 | 166.506s | 30 |
| pour_la_science | hybrid | gpt-oss:20b | 0.0 | 148.410s | 30 |
| faq | hybrid | gpt-oss:20b | 1.0 | 119.153s | 30 |

## 💻 Utilisation des ressources (moyennes globales)

| Ressource | Valeur |
|-----------|--------|
| CPU moyen | 21.9% |
| CPU max | 42.9% |
| RAM moyenne | 57.3% |
| RAM max | 59.3% |

## 📊 Détails par configuration

| Corpus | Mode | LLM | Multi-query | Temps (moy) | Temps (méd) | Min | Max | Écart-type | CPU avg | CPU max | RAM avg | RAM max | N |
|--------|------|-----|-------------|-------------|-------------|-----|-----|------------|---------|---------|---------|---------|---|
| faq | hybrid | gpt-oss:20b | 0.0 | 66.318s | 59.252s | 24.467s | 172.594s | 30.530s | 43.1% | 80.8% | 81.0% | 84.4% | 30 |
| faq | hybrid | gpt-oss:20b | 1.0 | 119.153s | 117.261s | 55.299s | 226.267s | 37.297s | 41.8% | 81.5% | 81.0% | 84.7% | 30 |
| faq | hybrid | llama3.2 | 0.0 | 3.977s | 3.842s | 2.477s | 7.583s | 1.143s | 17.5% | 24.0% | 37.3% | 38.7% | 30 |
| faq | hybrid | llama3.2 | 1.0 | 6.756s | 6.718s | 4.779s | 8.864s | 1.247s | 19.0% | 28.8% | 43.4% | 43.7% | 30 |
| faq | hybrid | nan | nan | 0.074s | 0.073s | 0.066s | 0.086s | 0.005s | 17.6% | 17.6% | 38.4% | 38.4% | 30 |
| faq | keyword | gpt-oss:20b | 0.0 | 8.486s | 7.287s | 3.531s | 25.421s | 4.869s | 5.3% | 22.9% | 89.6% | 90.4% | 30 |
| faq | keyword | gpt-oss:20b | 1.0 | 14.497s | 14.279s | 8.960s | 24.648s | 3.409s | 4.3% | 22.2% | 86.3% | 86.8% | 30 |
| faq | keyword | llama3.2 | 0.0 | 3.628s | 3.238s | 2.040s | 8.281s | 1.368s | 16.8% | 24.8% | 40.0% | 41.5% | 30 |
| faq | keyword | llama3.2 | 1.0 | 6.105s | 5.899s | 3.948s | 8.950s | 1.229s | 18.8% | 28.5% | 44.0% | 44.3% | 30 |
| faq | keyword | nan | nan | 0.056s | 0.056s | 0.036s | 0.066s | 0.008s | 9.9% | 9.9% | 30.4% | 30.4% | 30 |
| faq | neural | gpt-oss:20b | 0.0 | 60.085s | 56.818s | 26.503s | 150.008s | 26.003s | 41.9% | 82.5% | 80.7% | 85.0% | 30 |
| faq | neural | gpt-oss:20b | 1.0 | 104.532s | 94.279s | 49.740s | 277.942s | 46.452s | 46.4% | 80.2% | 80.9% | 84.9% | 30 |
| faq | neural | llama3.2 | 0.0 | 3.654s | 3.380s | 2.109s | 8.165s | 1.277s | 17.1% | 24.1% | 37.5% | 39.1% | 30 |
| faq | neural | llama3.2 | 1.0 | 6.036s | 5.854s | 4.435s | 10.871s | 1.352s | 19.6% | 26.7% | 42.7% | 43.0% | 30 |
| faq | neural | nan | nan | 0.066s | 0.059s | 0.051s | 0.283s | 0.041s | 15.9% | 15.9% | 37.7% | 37.7% | 30 |
| faq | semantic | gpt-oss:20b | 0.0 | 71.058s | 68.375s | 34.391s | 115.770s | 20.509s | 45.6% | 84.5% | 80.9% | 87.3% | 30 |
| faq | semantic | gpt-oss:20b | 1.0 | 105.162s | 103.737s | 56.874s | 165.866s | 27.829s | 42.5% | 89.3% | 80.2% | 88.2% | 30 |
| faq | semantic | llama3.2 | 0.0 | 5.335s | 5.030s | 3.691s | 9.976s | 1.292s | 14.5% | 26.9% | 41.2% | 43.3% | 30 |
| faq | semantic | llama3.2 | 1.0 | 7.838s | 7.707s | 6.125s | 10.432s | 1.153s | 14.2% | 26.1% | 47.7% | 49.0% | 30 |
| faq | semantic | nan | nan | 2.011s | 2.047s | 1.726s | 2.622s | 0.251s | 6.6% | 11.5% | 36.2% | 37.0% | 30 |
| pls | hybrid | nan | nan | 0.154s | 0.156s | 0.116s | 0.180s | 0.016s | 24.3% | 24.3% | 38.2% | 38.2% | 30 |
| pls | keyword | nan | nan | 0.149s | 0.150s | 0.106s | 0.240s | 0.024s | 20.8% | 20.8% | 30.7% | 30.7% | 30 |
| pls | neural | nan | nan | 0.063s | 0.063s | 0.043s | 0.072s | 0.005s | 16.8% | 16.8% | 37.9% | 37.9% | 30 |
| pls | semantic | nan | nan | 1.849s | 1.806s | 1.711s | 2.178s | 0.131s | 6.5% | 10.2% | 37.3% | 38.0% | 30 |
| pour_la_science | hybrid | gpt-oss:20b | 0.0 | 148.410s | 117.949s | 39.011s | 301.227s | 84.677s | 24.3% | 76.0% | 80.7% | 85.1% | 30 |
| pour_la_science | hybrid | gpt-oss:20b | 1.0 | 181.444s | 191.093s | 62.985s | 363.759s | 63.473s | 33.3% | 84.5% | 80.5% | 85.2% | 30 |
| pour_la_science | hybrid | llama3.2 | 0.0 | 9.429s | 9.157s | 4.650s | 15.037s | 2.871s | 17.5% | 37.9% | 41.7% | 42.2% | 28 |
| pour_la_science | hybrid | llama3.2 | 1.0 | 14.277s | 13.984s | 9.920s | 17.706s | 2.346s | 17.6% | 42.9% | 44.1% | 44.5% | 28 |
| pour_la_science | keyword | gpt-oss:20b | 0.0 | 17.415s | 15.636s | 6.537s | 31.990s | 6.128s | 4.0% | 21.8% | 89.5% | 90.2% | 30 |
| pour_la_science | keyword | gpt-oss:20b | 1.0 | 29.114s | 26.528s | 12.778s | 48.240s | 8.937s | 3.9% | 20.0% | 87.2% | 87.8% | 30 |
| pour_la_science | keyword | llama3.2 | 0.0 | 11.488s | 11.710s | 6.255s | 16.952s | 2.876s | 17.4% | 39.3% | 42.9% | 43.2% | 30 |
| pour_la_science | keyword | llama3.2 | 1.0 | 15.360s | 15.541s | 9.573s | 21.772s | 2.682s | 17.8% | 41.7% | 44.2% | 44.6% | 30 |
| pour_la_science | neural | gpt-oss:20b | 0.0 | 108.016s | 92.857s | 35.740s | 300.918s | 54.365s | 34.8% | 81.4% | 80.6% | 85.0% | 30 |
| pour_la_science | neural | gpt-oss:20b | 1.0 | 166.506s | 159.305s | 67.087s | 409.905s | 75.288s | 41.7% | 85.1% | 80.7% | 85.3% | 30 |
| pour_la_science | neural | llama3.2 | 0.0 | 7.856s | 7.477s | 3.070s | 15.741s | 2.628s | 16.8% | 32.5% | 40.2% | 40.5% | 30 |
| pour_la_science | neural | llama3.2 | 1.0 | 10.752s | 10.505s | 7.972s | 16.464s | 2.317s | 18.4% | 33.6% | 43.3% | 43.8% | 30 |
| pour_la_science | semantic | gpt-oss:20b | 0.0 | 110.215s | 93.823s | 22.441s | 304.366s | 67.417s | 33.1% | 81.3% | 80.5% | 87.3% | 30 |
| pour_la_science | semantic | gpt-oss:20b | 1.0 | 172.283s | 173.350s | 73.432s | 297.852s | 46.507s | 37.1% | 88.3% | 80.4% | 87.8% | 30 |
| pour_la_science | semantic | llama3.2 | 0.0 | 8.761s | 8.491s | 4.251s | 13.953s | 2.184s | 16.1% | 32.4% | 43.6% | 44.8% | 30 |
| pour_la_science | semantic | llama3.2 | 1.0 | 14.401s | 14.114s | 9.974s | 23.368s | 2.665s | 15.8% | 36.9% | 49.2% | 50.7% | 30 |

