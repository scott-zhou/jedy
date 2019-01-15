interface People {
    default int speed() {
        return 1;
    }

    static People getPeople(int v) {
        if (v % 3 == 1) {
            return new WhoRunFaster();
        }
        else if (v % 3 == 2){
            return new WhoRunSlower();
        }
        else {
            return new FakeRunner();
        }
    }
}
