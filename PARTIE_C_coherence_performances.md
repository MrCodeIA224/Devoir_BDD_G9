Partie 3 — Cohérence des données

3.1 Le théorème CAP

Quand une base de données est répartie sur plusieurs serveurs, le théorème CAP dit qu'on ne peut pas tout avoir. Trois propriétés existent : la cohérence (tous les serveurs donnent la même réponse au même moment), la disponibilité (le système répond toujours, même si un serveur est en panne) et la tolérance au partitionnement (le système continue de marcher quand les serveurs n'arrivent plus à communiquer entre eux).

On ne choisit pas la troisième : les pannes réseau arrivent forcément un jour. Le vrai choix est donc entre les deux premières. Un système CP préfère bloquer quelques instants plutôt que de donner une information peut être fausse. Un système AP préfère toujours répondre, quitte à donner une information un peu périmée. MongoDB est CP : si le serveur principal tombe, il met les écritures en pause le temps de désigner un remplaçant. Il préfère être juste que rapide.

3.2 ACID et BASE

CAP parle du système entier ; ACID et BASE parlent de ce qui se passe quand on écrit ou lit une donnée. ACID, c'est le contrat des bases SQL classiques : une opération réussit entièrement ou pas du tout, comme un virement bancaire, jamais d'entre-deux. C'est très sûr, mais lent quand plusieurs serveurs doivent se coordonner. BASE, c'est la philosophie NoSQL : le système répond presque toujours, et les copies finissent par se synchroniser, comme un message dans un groupe WhatsApp, que certains reçoivent tout de suite et d'autres dix secondes plus tard, mais que tout le monde finit par avoir. MongoDB se situe entre les deux, et nous laisse régler le curseur selon les besoins.

3.3 Et pour notre plateforme médicale ?

Ici, la cohérence n'est pas un détail technique : c'est une question de sécurité des patients. Si un médecin à Dakar note une allergie à la pénicilline et qu'un médecin à Thiès ouvre le dossier sans voir cette information, il peut prescrire un médicament dangereux. Attendre dix secondes que l'information se propage, c'est acceptable pour un like sur un réseau social, pas pour une allergie. Le choix CP de MongoDB correspond donc bien à notre besoin.

Une nuance quand même : toutes les données ne se valent pas. Une allergie, c'est vital. Un simple journal d'accès ("tel médecin a ouvert tel dossier à 14h32"), on en écrit des milliers par minute et en perdre un n'est pas grave. MongoDB permet justement de régler ce niveau de garantie donnée par donnée, grâce à deux paramètres, writeConcern et readConcern, qu'on étudie dans la section suivante.

