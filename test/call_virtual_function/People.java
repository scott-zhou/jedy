interface People {
    public int speed();

    public static People getPeople(int v) {
        if (v % 2 == 1) {
            return new WhoRunFaster();
        }
        else {
            return new WhoRunSlower();
        }
    }
}
