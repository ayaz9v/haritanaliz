# Yöntem

> **Durum: taslak (Adım 0).** Bu belge, proje tanımındaki analiz planını (K-021) ayrıntılandırır. Model belirlemesi, eşikler ve ağırlıklar ilgili adımlarda gerçek veriyle sınanacak; her değişiklik burada ve `docs/decisions.md`'de kayda geçecek. Sayısal parametrelerin tamamı `config/settings.yaml`'dadır.

## 1. Soru ve analiz birimi

Temel soru: bir bölgedeki işletme sayısı, bölgenin nüfusu, yoğunluğu, sosyoekonomik düzeyi, gündüz talebi ve erişilebilirliği göz önüne alındığında **beklenenden fazla mı, az mı?**

- **Temel birim:** mahalle/köy ($i$). Modeller bu düzeyde kurulur; il ve ilçe sonuçları mahalle/köy sonuçlarının toplanmasıyla elde edilir.
- **Kategori:** $k \in \{1,\dots,K\}$, başlangıçta $K = 23$ (`config/categories.yaml`). Her kategori için ayrı model kurulur.
- **H3 altıgenleri:** yoğunluk katmanları ve idari sınırlardan bağımsız bir sağlamlık kontrolü için kullanılır (çözünürlük 7, 8, 9). Aynı analizin iki farklı bölümlemeyle sonuç vermesi, değiştirilebilir alansal birim sorununa (MAUP) karşı bir sınamadır.

## 2. Veri hazırlama (özet)

| Değişken | Kaynak | Not |
|---|---|---|
| $y_{ik}$: işletme sayısı | Overture + OSM, eşleştirilmiş | yalnızca `operating_status` açık olanlar; güven skoru eşiği Adım 2'de |
| $P_i$: nüfus | TÜİK ADNKS | ikamet nüfusu; gündüz nüfusu değil |
| $A_i$: alan (km²) | OSM sınırı veya Voronoi yaklaşık sınırı | yaklaşık sınırlar işaretlenir |
| SEGE | il/ilçe SEGE | mahalleye üst birimden atanır |
| gündüz talebi | OSM: ofis, okul, hastane, AVM, istasyon, ticari/sanayi alanı | sayılar veya alan payları |
| erişilebilirlik | OSM yol ağı | ana yola ve merkeze uzaklık |

- **Özel bölgeler** (OSB, serbest bölge vb.): ikamet nüfusu çok az, işletme sayısı yüksek olabilir. Bu birimler nüfusa dayalı modelden çıkarılır; işletmeleri haritada ve toplam sayılarda korunur.
- **Küçük nüfuslu birimler:** $P_i <$ `analysis.min_population` olan birimlerde oranlar çok oynaktır. Bu birimler ayrı raporlanır; ayrıca ampirik Bayes yumuşatması değerlendirilecek.

## 3. Göstergeler

**10.000 kişiye düşen işletme:**

$$r_{ik} = 10^4 \cdot \frac{y_{ik}}{P_i}$$

**km² başına işletme:**

$$d_{ik} = \frac{y_{ik}}{A_i}$$

**Lokasyon katsayısı (LQ):** $k$ kategorisinin bölgedeki işletmeler içindeki payının Türkiye genelindeki payına oranı:

$$LQ_{ik} = \frac{y_{ik} / \sum_{k'} y_{ik'}}{Y_k / \sum_{k'} Y_{k'}}, \qquad Y_k = \sum_i y_{ik}$$

$LQ > 1$ bölgenin o kategoride göreli olarak uzmanlaştığını gösterir. LQ nüfustan bağımsızdır; bu yüzden $r_{ik}$ ile birlikte yorumlanır.

## 4. Beklenen sayı modeli

Her kategori için mahalle/köy düzeyinde bir sayım modeli:

$$y_{ik} \sim \text{Poisson}(\mu_{ik}) \quad \text{veya} \quad y_{ik} \sim \text{NB2}(\mu_{ik}, \alpha_k), \qquad \operatorname{Var}(y_{ik}) = \mu_{ik} + \alpha_k \mu_{ik}^2$$

$$
\log \mu_{ik} = \beta_{0k} + \beta_{1k} \log P_i + \beta_{2k} \log D_i + \beta_{3k}\, \text{SEGE}_{j(i)}
+ \boldsymbol{\gamma}_k^\top \mathbf{g}_i + \delta_{1k}\, u^{\text{yol}}_i + \delta_{2k}\, u^{\text{merkez}}_i + \eta_k\, \text{kent}_i + \lambda_{k,\,\text{il}(i)}
$$

- $\log P_i$ açıklayıcı olarak girer (offset olarak değil); böylece nüfus esnekliği $\beta_{1k}$ veriden tahmin edilir. $\beta_{1k} = 1$ kısıtı (offset) bir sağlamlık kontrolü olarak raporlanacak.
- $D_i$: nüfus yoğunluğu. $\mathbf{g}_i$: gündüz talebi göstergeleri. $u_i$: ana yola ve merkeze uzaklık. $\text{kent}_i$: kentsel/kırsal göstergesi. $\lambda_{k,\text{il}}$: il sabit etkileri.
- **Poisson mu, negatif binom mu?** Aşırı yayılım (overdispersion) testiyle seçilir: $H_0: \alpha_k = 0$. Sınamada Cameron–Trivedi yardımcı regresyonu ve olabilirlik oranı testi kullanılır. LR testinde $\alpha = 0$ parametre uzayının sınırında olduğundan p-değeri yarıya bölünür ($\bar\chi^2_{0:1}$ dağılımı). Anlamlılık düzeyi: `analysis.overdispersion_alpha` (0,05).
- **Fazla sıfır:** Köylerin çoğunda birçok kategori için sayı sıfırdır. Sıfır şişirilmiş (ZINB) ve engel (hurdle) modelleri sağlamlık kontrolü olarak denenecek.
- **Araç:** `statsmodels` (GLM Poisson, NegativeBinomial, ZeroInflatedNegativeBinomialP).

## 5. Doygunluk skoru

Gözlenen ve beklenen sayının farkı, Pearson artığıyla ölçeklenir:

$$e_{ik} = \frac{y_{ik} - \hat\mu_{ik}}{\sqrt{\hat V_{ik}}}, \qquad \hat V_{ik} = \hat\mu_{ik} \;\; (\text{Poisson}), \qquad \hat V_{ik} = \hat\mu_{ik} + \hat\alpha_k \hat\mu_{ik}^2 \;\; (\text{NB2})$$

| Sınıf | Koşul (varsayılan) |
|---|---|
| fazla | $e_{ik} > 2$ (`analysis.saturation.surplus_threshold`) |
| dengeli | $-2 \le e_{ik} \le 2$ |
| eksik | $e_{ik} < -2$ (`analysis.saturation.deficit_threshold`) |

Arayüzde sınıfın yanında gözlenen ve beklenen sayı birlikte gösterilir ("12 eczane var, model 7 bekliyor"). Beklenen sayı çok küçükse ($\hat\mu < 1$) sınıf yerine "yetersiz veri" gösterilmesi değerlendirilecek.

## 6. Mekânsal analiz

1. **Komşuluk:** mahalle/köy poligonlarından queen komşuluk matrisi, satır standardizasyonuyla (`libpysal`).
2. **Moran's I:** model artıklarında mekânsal öz ilişki, permütasyonla çıkarım (`esda`). Yerel göstergeler (LISA) sıcak/soğuk noktalar için ayrıca hesaplanır.
3. **Model seçimi:** artıklarda anlamlı öz ilişki varsa Lagrange çarpanı testleriyle (Anselin) mekânsal gecikme ve mekânsal hata modelleri karşılaştırılır (`spreg`).
4. **Sayım verisi uyarısı:** `spreg` modelleri doğrusaldır. Sayım verisinde iki yol değerlendirilecek: (a) $\log(1 + r_{ik})$ gibi dönüştürülmüş oranlarla doğrusal mekânsal modeller, (b) GLM'e mekânsal filtre (Moran özvektörleri) eklemek. Seçim, analiz adımında veriyle yapılacak.

## 7. Tedarik ve erişilebilirlik skoru (0–100)

Bileşenler (taslak): ana yola uzaklık, ilçe/il merkezine uzaklık, toptancı ve tedarik noktalarına (hal, toptan satış, sanayi alanı) uzaklık, toplu taşıma durak yoğunluğu. Her bileşen yüzdelik sıraya çevrilir (uzaklıklarda ters yönde), ağırlıklı ortalaması 0–100'e ölçeklenir. Bileşen ağırlıkları `config/settings.yaml`'a eklenecek.

## 8. Fırsat skoru

Mod 2'de (fırsat arama) mahalleler, seçilen kategori için şu skorla sıralanır:

$$F_{ik} = w_e \, E_{ik} + w_a \, A_i + w_t \, T_i, \qquad w_e + w_a + w_t = 1$$

- $E_{ik}$: eksiklik; $\max(0, -e_{ik})$ değerinin yüzdelik sırası.
- $A_i$: erişilebilirlik skoru (0–1'e ölçeklenmiş).
- $T_i$: talep; nüfus ve gündüz talebi göstergelerinin yüzdelik sırası.
- Varsayılan ağırlıklar (`analysis.opportunity_weights`): $w_e = 0{,}5$, $w_a = 0{,}25$, $w_t = 0{,}25$. Doğrulama, ağırlıkların toplamının 1 olmasını zorunlu kılar.

## 9. Veri güven düzeyi

Her bölge-kategori sonucu için 0–1 arası bir güven skoru hesaplanır ve sınıfa çevrilir: yüksek (≥ 0,75), orta (≥ 0,5), düşük. Eşikler `analysis.confidence`'tadır. Skora giren bileşenler (taslak):

- işletmelerin iki kaynakta birden (Overture ve OSM) bulunma oranı ve Overture `confidence` ortalaması,
- sınırın gerçek mi yaklaşık (Voronoi) mı olduğu,
- beklenen sayının büyüklüğü (küçük sayılarda belirsizlik yüksektir),
- özel bölge (OSB vb.) ve küçük nüfus işaretleri.

Güven düzeyi ve veri tarihi her sonuçla birlikte arayüzde gösterilir.

## 10. Bilinen sınırlamalar

- **Kapsam farkı:** OSM ve Overture kırsal alanlarda işletmeleri eksik içerebilir. Bu durumda "eksik" sınıfı gerçek bir açıktan değil, veri eksikliğinden kaynaklanabilir. Güven düzeyi bu riski görünür kılmak için var.
- **Kategori gürültüsü:** Kaynaklar arasında kategori eşleşmesi kusurludur (ör. pastane ile tatlıcı, bakkal ile market). Eşlemeler Adım 2'de veriyle doğrulanacak.
- **İkamet nüfusu:** ADNKS gündüz nüfusunu ve turist nüfusunu ölçmez. Gündüz talebi göstergeleri bunu kısmen telafi eder.
- **Zaman uyumsuzluğu:** nüfus yıllık, işletme verisi aylık güncellenir.
- **Ekolojik çıkarım:** sonuçlar bölgeler hakkındadır; tek tek işletmeler veya kişiler hakkında değildir.
- **Nedensellik yok:** model koşullu bir beklenti verir; "eksik" bir bölgede yeni bir işletmenin başarılı olacağını garanti etmez.

## 11. Doğrulama planı

- Kategori kapsamını, il bazında kamuya açık resmî veya meslek kuruluşu sayımlarıyla (ör. eczane sayıları) karşılaştırmak.
- Örneklem dışı tahmin: illerin bir kısmını dışarıda bırakıp modelin onlardaki sayıları tahmin gücü.
- Model artıklarının dağılımı ve Moran's I; idari birim ile H3 sonuçlarının tutarlılığı.
