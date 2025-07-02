# ObFUSE

A filesystem that obfuscates the location of all files inside a directory.

---

| Unmounted                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Mounted                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ➜ tree<br>.<br>├── 4dZn7G83<br>├── 4mT01QqKd<br>├── 5BRY4aP<br>├── 5jN9QTZn8<br>├── 5uGOM0J<br>├── 7GbD9apkx<br>├── citBkYG<br>├── FhSDmsHIZ<br>├── hZjUZzM<br>├── i2XZrgqSv<br>├── I6cY5dn<br>├── JI5haYLU9<br>├── js7lymk<br>├── kBSO0blq7<br>├── khcuAV5<br>├── kjgC3HnbB<br>├── KONOezM<br>├── lJ5hTA6PX<br>├── nd0URwa<br>├── o320cT19J<br>├── obfusfs.db<br>├── oZLAUYvKW<br>├── PiLkCN2<br>├── qiRHMyHT3<br>├── QMMgDkS<br>├── rjULUt1Dv<br>├── thxNqoo<br>├── tiwZa7LxU<br>├── TIzr1iN<br>├── uhhpjEGaW<br>├── uI6eO2L<br>├── uZ0Mg7lZs<br>├── vaiS1kU<br>├── VPKXowmqT<br>└── YnqeeXuvK<br><br>1 directory, 35 files | ➜ tree<br>.<br>├── artworks<br>│ ├── harusanme<br>│ │ └── conductor.png<br>│ ├── jongsujin<br>│ │ └── shigatito.jpg<br>│ ├── koudeinn<br>│ │ └── umbrella.png<br>│ ├── novanovase<br>│ │ └── cfcomms.jpg<br>│ ├── pizbhao<br>│ │ └── art.png<br>│ ├── ShizuRefResized.jpg<br>│ ├── skaiede<br>│ │ └── butler.jpg<br>│ ├── toru_r8<br>│ │ └── nature.png<br>│ ├── vixx<br>│ │ └── train.jpg<br>└── protohackers<br> ├── chall-0<br> │ └── main.go<br> ├── chall-1<br> │ └── main.go<br> └── go.mod<br><br>25 directories, 34 files |

## How It Works

There are two directories:

- Mapped directory: The FUSE mounted FS, where you will be interacting with the files
- Data directory: The actual directory in your real disk where all the files will be stored. All the file name is obfuscated, **but the content isn't.**

Whenever you make or copy a file into the mapped directory, it'll assign a random string of character for that file. It will then save the content of the file to the data directory.

The FS will remember and keep track of the mapping as the file is added, removed, or moved around.

## Directories in ObFUSE

In ObFUSE, the directory in the mapped FS will not be reflected in the data directory. As in, the data directory will never have subdirectories. All the directory data is saved virtually in the mapping database.
