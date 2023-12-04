#!/bin/zsh

#mkdir vidyut-tiN
#mkdir vidyut-tiN-akartari
#mkdir vidyut-Nich-tiN  
#mkdir vidyut-Nich-akartari  
#mkdir vidyut-san-tiN  
#mkdir vidyut-san-akartari  
#mkdir vidyut-yaN-tiN  
#mkdir vidyut-yaN-akartari  
#mkdir vidyut-yaN-luk-tiN  
#mkdir vidyut-yaN-luk-akartari

cargo run --release --example create_tinantas_babylon -- --desc "vidyud-yantreRa janitAni tiNantAni " > /home/vvasuki/gitland/indic-dict_stardict/stardict-sanskrit-vyAkaraNa/tiNanta/vidyut/vidyut-tiN/vidyut-tiNanta.babylon
cargo run --release --example create_tinantas_babylon -- --prayoga karmani --desc "vidyud-yantreRa janitAni tiNantAni (akartari)" > /home/vvasuki/gitland/indic-dict_stardict/stardict-sanskrit-vyAkaraNa/tiNanta/vidyut/vidyut-tiN-akartari/vidyut-tiNanta-akartari.babylon


cargo run --release --example create_tinantas_babylon -- --sanadi san --desc "vidyud-yantreRa janitAni sannteByas tiNantAni" > /home/vvasuki/gitland/indic-dict_stardict/stardict-sanskrit-vyAkaraNa/tiNanta/vidyut/vidyut-san-tiN/vidyut-san-tiN.babylon
cargo run --release --example create_tinantas_babylon -- --sanadi san --prayoga karmani --desc "vidyud-yantreRa janitAni sannteByas tiNantAni (akartari)" > /home/vvasuki/gitland/indic-dict_stardict/stardict-sanskrit-vyAkaraNa/tiNanta/vidyut/vidyut-san-akartari/vidyut-san-akartari.babylon

cargo run --release --example create_tinantas_babylon -- --sanadi Ric --desc "vidyud-yantreRa janitAni RicanteByas tiNantAni" > /home/vvasuki/gitland/indic-dict_stardict/stardict-sanskrit-vyAkaraNa/tiNanta/vidyut/vidyut-Nich-tiN/vidyut-Nich-tiN.babylon
cargo run --release --example create_tinantas_babylon -- --prayoga karmani --sanadi Ric --desc "vidyud-yantreRa janitAni RicanteByas tiNantAni (akartari)" > /home/vvasuki/gitland/indic-dict_stardict/stardict-sanskrit-vyAkaraNa/tiNanta/vidyut/vidyut-Nich-akartari/vidyut-Nich-akartari.babylon

cargo run --release --example create_tinantas_babylon -- --sanadi yaN --desc "vidyud-yantreRa janitAni yaNNanteByas tiNantAni" > /home/vvasuki/gitland/indic-dict_stardict/stardict-sanskrit-vyAkaraNa/tiNanta/vidyut/vidyut-yaN-tiN/vidyut-yaN-tiN.babylon
cargo run --release --example create_tinantas_babylon -- --sanadi yaN --prayoga karmani --desc "vidyud-yantreRa janitAni yaNNanteByas tiNantAni (akartari)" > /home/vvasuki/gitland/indic-dict_stardict/stardict-sanskrit-vyAkaraNa/tiNanta/vidyut/vidyut-yaN-akartari/vidyut-yaN-akartari.babylon

cargo run --release --example create_tinantas_babylon -- --sanadi yaNluk --desc "vidyud-yantreRa janitAni yaNluganteByas tiNantAni" > /home/vvasuki/gitland/indic-dict_stardict/stardict-sanskrit-vyAkaraNa/tiNanta/vidyut/vidyut-yaN-luk-tiN/vidyut-yaN-luk-tiN.babylon
cargo run --release --example create_tinantas_babylon -- --sanadi yaNluk --prayoga karmani --desc "vidyud-yantreRa janitAni yaNluganteByas tiNantAni (akartari)" > /home/vvasuki/gitland/indic-dict_stardict/stardict-sanskrit-vyAkaraNa/tiNanta/vidyut/vidyut-yaN-luk-akartari/vidyut-yaN-luk-akartari.babylon
